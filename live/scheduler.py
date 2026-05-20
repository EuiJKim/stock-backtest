from datetime import datetime, time as dtime
import threading


def should_trigger(now: datetime, target_time: dtime,
                   last_action_date: str) -> bool:
    if now.weekday() >= 5:  # 주말 제외
        return False
    if now.time() < target_time:
        return False
    if last_action_date == now.date().isoformat():
        return False
    return True


class Scheduler:
    def __init__(self, target_time, on_trigger, tick_seconds=30,
                 clock=datetime.now):
        self.target_time = target_time
        self.on_trigger = on_trigger
        self.tick_seconds = tick_seconds
        self.clock = clock
        self._stop = threading.Event()
        self._thread = None

    def start(self, state_provider) -> None:
        def _run():
            while not self._stop.is_set():
                now = self.clock()
                state = state_provider()
                if (not getattr(state, "halted", False)
                        and should_trigger(now, self.target_time,
                                           getattr(state, "last_action_date",
                                                   ""))):
                    try:
                        self.on_trigger()
                    except Exception:
                        pass  # GUI 로그어가 상위에서 잡음
                self._stop.wait(self.tick_seconds)
        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
