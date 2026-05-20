import logging
from live.executor import execute
from live.runner import Decision, Order
from live.state import Holding, TraderState, TraderParams


class FakeBroker:
    def __init__(self, quote=10000.0, balance=None, fill="FILLED"):
        self.quote = quote
        self._balance = balance or {"cash": 5_000_000.0,
                                     "equity": 10_000_000.0}
        self.placed = []
        self._next_id = 0
        self._fill = fill

    def get_quote(self, code): return self.quote
    def get_balance(self): return dict(self._balance)
    def get_holdings(self): return {}

    def place_order(self, code, side, qty):
        self._next_id += 1
        oid = f"ORD-{self._next_id}"
        self.placed.append((oid, code, side, qty))
        return oid

    def get_order_status(self, order_id):
        # 마지막 주문 정보로부터 체결가 모사
        _, code, side, qty = next(p for p in self.placed if p[0] == order_id)
        return {"order_id": order_id, "status": self._fill,
                "filled_qty": qty, "fill_price": self.quote}


def _logger():
    return logging.getLogger("test")


def _safety():
    return {"max_position_pct": 0.40, "min_order_amount": 10_000.0,
            "max_daily_loss": 0.05}


def test_noop_returns_true_without_orders():
    broker = FakeBroker()
    state = TraderState(equity_start_of_day=10_000_000.0)
    ok = execute(Decision(action="NOOP", orders=[], reason=""),
                  broker, state, _safety(), _logger())
    assert ok is True
    assert broker.placed == []


def test_rebalance_sells_then_buys_and_updates_state():
    broker = FakeBroker(quote=10_000.0)
    state = TraderState(mode="paper", cash=0.0,
                        holdings={"OLD": Holding(shares=5,
                                                 entry_price=20_000.0)},
                        equity_start_of_day=10_000_000.0)
    d = Decision(action="REBALANCE", orders=[
        Order(code="OLD", side="SELL", qty=5, reason="rebalance"),
        Order(code="NEW", side="BUY", qty=100, reason="rebalance"),
    ])
    ok = execute(d, broker, state, _safety(), _logger())
    assert ok is True
    # SELL이 BUY보다 먼저 호출됨
    sides = [p[2] for p in broker.placed]
    assert sides == ["SELL", "BUY"]
    # 상태 업데이트
    assert "OLD" not in state.holdings
    assert state.holdings["NEW"].shares == 100
    assert state.holdings["NEW"].entry_price == 10_000.0


def test_position_limit_blocks_buy_but_keeps_state_safe():
    # 단가 너무 비싸서 한도 초과 → 매수 스킵
    broker = FakeBroker(quote=1_000_000.0)  # 100주 = 1억
    state = TraderState(mode="paper", cash=10_000_000.0,
                        equity_start_of_day=10_000_000.0)
    d = Decision(action="REBALANCE", orders=[
        Order(code="X", side="BUY", qty=100, reason="rebalance"),
    ])
    ok = execute(d, broker, state, _safety(), _logger())
    assert ok is True
    # 주문 안 됨
    assert broker.placed == []
    assert "X" not in state.holdings


def test_rejected_order_halts_state():
    broker = FakeBroker(quote=10_000.0, fill="REJECTED")
    state = TraderState(mode="paper", cash=10_000_000.0,
                        equity_start_of_day=10_000_000.0)
    d = Decision(action="REBALANCE", orders=[
        Order(code="X", side="BUY", qty=100, reason="rebalance"),
    ])
    ok = execute(d, broker, state, _safety(), _logger())
    assert ok is False
    assert state.halted is True


def test_daily_loss_kill_halts():
    broker = FakeBroker(balance={"cash": 0.0, "equity": 9_000_000.0})
    state = TraderState(mode="paper", equity_start_of_day=10_000_000.0)
    d = Decision(action="REBALANCE", orders=[
        Order(code="X", side="BUY", qty=100, reason="rebalance"),
    ])
    ok = execute(d, broker, state, _safety(), _logger())
    assert ok is False
    assert state.halted is True
    assert broker.placed == []


def test_live_mode_rejected():
    broker = FakeBroker()
    state = TraderState(mode="live", equity_start_of_day=10_000_000.0)
    d = Decision(action="REBALANCE", orders=[
        Order(code="X", side="BUY", qty=1, reason="rebalance")])
    ok = execute(d, broker, state, _safety(), _logger())
    assert ok is False
    assert state.halted is True
