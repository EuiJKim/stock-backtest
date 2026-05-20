import logging
import threading
from dataclasses import dataclass
from datetime import datetime, time as dtime
from pathlib import Path

from broker.credentials import Credentials
from broker.kiwoom import KiwoomClient
from gui.app import TraderApp, GuiLogHandler, _build_app_class
from live.executor import execute
from live.runner import decide
from live.safety import is_market_open, holdings_drift_ok
from live.scheduler import Scheduler
from live.state import TraderState, TraderParams
from live.universe_store import UniverseStore

DEFAULT_SECRETS = Path("secrets/kiwoom.json")
DEFAULT_STATE = Path("state/trader_state.json")
DEFAULT_PARAMS = Path("state/trader_params.json")
DEFAULT_UNIVERSE = Path("state/universe.json")
DEFAULT_LOG = Path("state/trader.log")


@dataclass
class TraderComponents:
    credentials: Credentials
    state: TraderState
    params: TraderParams
    universe: UniverseStore
    broker: KiwoomClient
    scheduler: Scheduler
    app: TraderApp


def _parse_hhmm(s: str) -> dtime:
    h, m = s.split(":")
    return dtime(int(h), int(m))


def run_trader_tick(broker, state, params, universe_codes, log,
                    state_path, stop_event=None, now=None, panels_loader=None):
    """One scheduled tick.

    1. Skip outside KRX hours (Fix 4).
    2. Snapshot day-start equity on first trigger of each day (Fix 2).
    3. Halt if broker holdings have drifted beyond tolerance (Fix 3).
    4. Build panels, decide, execute.
    5. Persist state.

    Returns a string action label:
      "market_closed" | "drift_halt" | "<Decision.action>"
    """
    now = now or datetime.now()
    today_str = now.date().isoformat()

    # Stop event guard — abort immediately if halted externally
    if stop_event is not None and stop_event.is_set():
        return "stopped"

    # Fix 4 — market hours guard
    if not is_market_open(now):
        log.info("outside KRX hours; skipping")
        return "market_closed"

    # Fix 2 — snapshot equity at start of day
    if state.last_action_date != today_str or state.equity_start_of_day == 0.0:
        try:
            bal = broker.get_balance()
            state.equity_start_of_day = bal.get("equity", 0.0)
            log.info(f"day-start equity snapshotted: {state.equity_start_of_day:.0f}")
        except Exception as e:
            log.error(f"equity snapshot failed: {e}")
            state.halted = True
            if stop_event is None or not stop_event.is_set():
                state.save(state_path)
            return "drift_halt"

    # Fix 3 — drift guard
    try:
        broker_holdings = broker.get_holdings()
    except Exception as e:
        log.error(f"holdings fetch failed: {e}")
        state.halted = True
        if stop_event is None or not stop_event.is_set():
            state.save(state_path)
        return "drift_halt"

    if not holdings_drift_ok(state.holdings, broker_holdings,
                              params.drift_tolerance):
        log.warning(
            "holdings drift exceeds tolerance — halting for manual review. "
            f"state={state.holdings}, broker={broker_holdings}"
        )
        state.halted = True
        if stop_event is None or not stop_event.is_set():
            state.save(state_path)
        return "drift_halt"

    # Build price panels
    if panels_loader is None:
        from data.loader import build_panels as _build_panels

        def panels_loader(codes):  # noqa: E731
            close, _ = _build_panels(codes,
                                     "2024-01-01",
                                     now.date().isoformat(),
                                     "data/cache")
            return close

    try:
        close = panels_loader(universe_codes)
    except Exception as e:
        log.exception(f"panels load failed: {e}")
        state.halted = True
        if stop_event is None or not stop_event.is_set():
            state.save(state_path)
        return "drift_halt"

    safety_params = {
        "max_position_pct": params.max_position_pct,
        "min_order_amount": params.min_order_amount,
        "max_daily_loss": params.max_daily_loss,
    }

    try:
        balance = broker.get_balance()
        decision = decide(close, now.date(),
                          state.holdings, balance.get("cash", 0.0),
                          params, state)
        ok = execute(decision, broker, state, safety_params, log, now=now,
                     stop_event=stop_event)
        if stop_event is None or not stop_event.is_set():
            state.save(state_path)
        log.info(f"trigger 완료 ok={ok} action={decision.action} "
                 f"reason={decision.reason}")
        return decision.action
    except Exception as e:
        log.exception(f"trigger 실패: {e}")
        state.halted = True
        if stop_event is None or not stop_event.is_set():
            state.save(state_path)
        return "error"


def build_components(secrets_path=DEFAULT_SECRETS,
                     state_path=DEFAULT_STATE,
                     params_path=DEFAULT_PARAMS,
                     universe_path=DEFAULT_UNIVERSE,
                     log=None,
                     app_master=None) -> TraderComponents:
    log = log or logging.getLogger("trader")
    creds = Credentials.load(secrets_path=secrets_path)
    state = TraderState.load(state_path)
    state.mode = creds.mode  # 자격증명 모드를 신뢰
    params = TraderParams.load(params_path)
    universe = UniverseStore.load(universe_path)
    broker = KiwoomClient(base_url=creds.base_url,
                          app_key=creds.app_key,
                          app_secret=creds.app_secret,
                          account_no=creds.account_no)

    stop_event = threading.Event()

    def on_trigger():
        run_trader_tick(
            broker=broker,
            state=state,
            params=params,
            universe_codes=universe.codes(),
            log=log,
            state_path=state_path,
            stop_event=stop_event,
        )

    scheduler = Scheduler(target_time=_parse_hhmm(params.target_time_hhmm),
                          on_trigger=on_trigger, tick_seconds=30,
                          stop_event=stop_event)

    def on_start():
        scheduler.start(state_provider=lambda: state)
        log.info("자동매매 시작")
        app.refresh_mode()

    def on_stop():
        state.halted = True        # mark halted FIRST
        state.save(state_path)     # persist
        scheduler.stop()           # then signal scheduler
        log.info("자동매매 정지 (HALTED)")
        app.refresh_mode()

    if app_master is not None:
        import tkinter as tk
        _AppClass = _build_app_class(tk.Toplevel)
        app = _AppClass(state=state, params=params, universe=universe,
                        on_start=on_start, on_stop=on_stop,
                        params_path=params_path, universe_path=universe_path,
                        master=app_master)
    else:
        app = TraderApp(state=state, params=params, universe=universe,
                        on_start=on_start, on_stop=on_stop,
                        params_path=params_path, universe_path=universe_path)

    # Fix 5 — wire GUI log panel to stdlib logger
    gui_handler = GuiLogHandler(app)
    gui_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(gui_handler)

    return TraderComponents(credentials=creds, state=state, params=params,
                             universe=universe, broker=broker,
                             scheduler=scheduler, app=app)


def main():
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("trader")
    Path("state").mkdir(parents=True, exist_ok=True)

    # Fix 6 — FileHandler with formatter
    fh = logging.FileHandler(DEFAULT_LOG, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(fh)

    comps = build_components(log=log)
    comps.app.mainloop()


if __name__ == "__main__":
    main()
