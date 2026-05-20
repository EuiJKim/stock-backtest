import logging
from dataclasses import dataclass
from datetime import datetime, time as dtime
from pathlib import Path

from broker.credentials import Credentials
from broker.kiwoom import KiwoomClient
from gui.app import TraderApp
from live.executor import execute
from live.runner import decide
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


def build_components(secrets_path=DEFAULT_SECRETS,
                     state_path=DEFAULT_STATE,
                     params_path=DEFAULT_PARAMS,
                     universe_path=DEFAULT_UNIVERSE,
                     log=None) -> TraderComponents:
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

    safety_params = {
        "max_position_pct": params.max_position_pct,
        "min_order_amount": params.min_order_amount,
        "max_daily_loss": params.max_daily_loss,
    }

    def on_trigger():
        try:
            from data.loader import build_panels
            close, _ = build_panels(universe.codes(),
                                     "2024-01-01",
                                     datetime.now().date().isoformat(),
                                     "data/cache")
            balance = broker.get_balance()
            holdings = broker.get_holdings()  # broker live; state 보유와 비교는 다음 단계 spec
            decision = decide(close, datetime.now().date(),
                               state.holdings, balance.get("cash", 0.0),
                               params, state)
            ok = execute(decision, broker, state, safety_params, log,
                          now=datetime.now())
            state.save(state_path)
            log.info(f"trigger 완료 ok={ok} action={decision.action} "
                     f"reason={decision.reason}")
        except Exception as e:
            log.exception(f"trigger 실패: {e}")
            state.halted = True
            state.save(state_path)

    scheduler = Scheduler(target_time=_parse_hhmm(params.target_time_hhmm),
                          on_trigger=on_trigger, tick_seconds=30)

    def on_start():
        scheduler.start(state_provider=lambda: state)
        log.info("자동매매 시작")
        app.refresh_mode()

    def on_stop():
        scheduler.stop()
        state.halted = True
        state.save(state_path)
        log.info("자동매매 정지 (HALTED)")
        app.refresh_mode()

    app = TraderApp(state=state, params=params, universe=universe,
                     on_start=on_start, on_stop=on_stop)

    return TraderComponents(credentials=creds, state=state, params=params,
                             universe=universe, broker=broker,
                             scheduler=scheduler, app=app)


def main():
    logging.basicConfig(level=logging.INFO,
                         format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("trader")
    Path("state").mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(DEFAULT_LOG, encoding="utf-8")
    fh.setLevel(logging.INFO)
    log.addHandler(fh)
    comps = build_components(log=log)
    comps.app.mainloop()


if __name__ == "__main__":
    main()
