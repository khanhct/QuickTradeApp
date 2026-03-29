"""Mock MT5 module for development on non-Windows platforms.
Simulates MT5 API responses with fake data.
"""
import time
import random
from dataclasses import dataclass

# Constants matching MT5
TRADE_ACTION_DEAL = 1
TRADE_ACTION_PENDING = 5
TRADE_ACTION_SLTP = 6
TRADE_ACTION_REMOVE = 8

ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1
ORDER_TYPE_BUY_LIMIT = 2
ORDER_TYPE_SELL_LIMIT = 3

ORDER_TIME_GTC = 0
ORDER_FILLING_IOC = 1
ORDER_FILLING_RETURN = 2

TRADE_RETCODE_DONE = 10009


@dataclass
class _TerminalInfo:
    name: str = "MetaTrader 5 (Mock)"
    build: int = 9999
    connected: bool = True
    trade_allowed: bool = True


@dataclass
class _Tick:
    ask: float = 0.0
    bid: float = 0.0
    time: int = 0


@dataclass
class _Position:
    ticket: int = 0
    symbol: str = ""
    type: int = 0
    volume: float = 0.0
    price_open: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    profit: float = 0.0
    time: int = 0
    magic: int = 0
    comment: str = ""


@dataclass
class _Order:
    ticket: int = 0
    symbol: str = ""
    type: int = 0
    volume_current: float = 0.0
    price_open: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    time_setup: int = 0
    magic: int = 0
    comment: str = ""


@dataclass
class _OrderResult:
    retcode: int = TRADE_RETCODE_DONE
    order: int = 0
    comment: str = "Mock order executed"


# Internal state
_initialized = False
_positions: list[_Position] = []
_orders: list[_Order] = []
_next_ticket = 100001


def _generate_mock_positions():
    """Generate some fake positions for testing."""
    global _positions, _next_ticket
    base_prices = {
        "XAUUSD": 3020.50,
        "EURUSD": 1.0850,
        "GBPUSD": 1.2650,
    }
    _positions = []
    for symbol, base_price in base_prices.items():
        for i in range(random.randint(1, 3)):
            pos_type = random.choice([ORDER_TYPE_BUY, ORDER_TYPE_SELL])
            price = base_price + random.uniform(-5, 5)
            _positions.append(_Position(
                ticket=_next_ticket,
                symbol=symbol,
                type=pos_type,
                volume=round(random.choice([0.01, 0.02, 0.05, 0.1]), 2),
                price_open=round(price, 5),
                sl=round(price - 10 if pos_type == 0 else price + 10, 5),
                tp=0.0,
                profit=round(random.uniform(-50, 100), 2),
                time=int(time.time()) - random.randint(60, 3600),
                comment="mock",
            ))
            _next_ticket += 1


def initialize(**kwargs) -> bool:
    global _initialized
    _initialized = True
    _generate_mock_positions()
    return True


def shutdown():
    global _initialized
    _initialized = False


def terminal_info():
    if _initialized:
        return _TerminalInfo()
    return None


def last_error():
    return (-1, "Mock error")


def symbol_info_tick(symbol: str):
    base_prices = {
        "XAUUSD": 3020.50,
        "EURUSD": 1.0850,
        "GBPUSD": 1.2650,
        "USDJPY": 150.25,
    }
    base = base_prices.get(symbol, 100.0)
    spread = 0.5 if "XAU" in symbol else 0.0002
    return _Tick(
        ask=round(base + spread, 5),
        bid=round(base, 5),
        time=int(time.time()),
    )


def positions_get(symbol: str = None, ticket: int = None):
    if not _initialized:
        return None

    # Simulate small profit changes
    for p in _positions:
        p.profit = round(p.profit + random.uniform(-2, 2), 2)

    if ticket is not None:
        result = [p for p in _positions if p.ticket == ticket]
        return result if result else None
    if symbol is not None:
        result = [p for p in _positions if p.symbol == symbol]
        return result if result else ()
    return tuple(_positions)


def orders_get(symbol: str = None, ticket: int = None):
    """Get pending orders."""
    if not _initialized:
        return None

    if ticket is not None:
        result = [o for o in _orders if o.ticket == ticket]
        return result if result else None
    if symbol is not None:
        result = [o for o in _orders if o.symbol == symbol]
        return result if result else ()
    return tuple(_orders)


def order_send(request: dict):
    global _next_ticket, _positions

    action = request.get("action")
    ticket = _next_ticket
    _next_ticket += 1

    if action == TRADE_ACTION_SLTP:
        # Modify SL/TP
        pos_ticket = request.get("position")
        for p in _positions:
            if p.ticket == pos_ticket:
                p.sl = request.get("sl", p.sl)
                p.tp = request.get("tp", p.tp)
                break
        return _OrderResult(retcode=TRADE_RETCODE_DONE, order=pos_ticket, comment="SL/TP modified")

    if action == TRADE_ACTION_DEAL:
        pos_ticket = request.get("position")
        if pos_ticket:
            # Close position
            _positions = [p for p in _positions if p.ticket != pos_ticket]
            return _OrderResult(retcode=TRADE_RETCODE_DONE, order=ticket, comment="Position closed")
        else:
            # New market order
            _positions.append(_Position(
                ticket=ticket,
                symbol=request["symbol"],
                type=request["type"],
                volume=request["volume"],
                price_open=request["price"],
                sl=request.get("sl", 0.0),
                tp=request.get("tp", 0.0),
                profit=0.0,
                time=int(time.time()),
                comment="mock order",
            ))
            return _OrderResult(retcode=TRADE_RETCODE_DONE, order=ticket, comment="Market order filled")

    if action == TRADE_ACTION_PENDING:
        _orders.append(_Order(
            ticket=ticket,
            symbol=request["symbol"],
            type=request["type"],
            volume_current=request["volume"],
            price_open=request["price"],
            sl=request.get("sl", 0.0),
            tp=request.get("tp", 0.0),
            time_setup=int(time.time()),
            comment="mock pending",
        ))
        return _OrderResult(retcode=TRADE_RETCODE_DONE, order=ticket, comment="Pending order placed")

    if action == TRADE_ACTION_REMOVE:
        order_ticket = request.get("order")
        _orders[:] = [o for o in _orders if o.ticket != order_ticket]
        return _OrderResult(retcode=TRADE_RETCODE_DONE, order=order_ticket, comment="Order cancelled")

    return _OrderResult(retcode=TRADE_RETCODE_DONE, order=ticket)
