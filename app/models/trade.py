from dataclasses import dataclass
from typing import Optional


@dataclass
class Position:
    ticket: int
    symbol: str
    type: int  # 0=BUY, 1=SELL
    volume: float
    price_open: float
    sl: float
    tp: float
    profit: float
    time: int
    magic: int = 0
    comment: str = ""

    @property
    def type_str(self) -> str:
        return "BUY" if self.type == 0 else "SELL"


@dataclass
class PendingOrder:
    ticket: int
    symbol: str
    type: int  # ORDER_TYPE_BUY_LIMIT=2, SELL_LIMIT=3, BUY_STOP=4, SELL_STOP=5
    volume: float
    price_open: float  # requested price
    sl: float
    tp: float
    time: int
    magic: int = 0
    comment: str = ""

    _TYPE_NAMES = {
        2: "BUY LIMIT",
        3: "SELL LIMIT",
        4: "BUY STOP",
        5: "SELL STOP",
        6: "BUY STOP LIMIT",
        7: "SELL STOP LIMIT",
    }

    @property
    def type_str(self) -> str:
        return self._TYPE_NAMES.get(self.type, f"TYPE_{self.type}")

    @property
    def is_buy(self) -> bool:
        return self.type in (2, 4, 6)


@dataclass
class TradeRequest:
    symbol: str
    order_type: str  # "buy" or "sell"
    lot: float
    price: Optional[float] = None  # None for market orders
    sl: Optional[float] = None
    tp: Optional[float] = None
    is_market: bool = True


@dataclass
class TradeResult:
    success: bool
    ticket: int = 0
    comment: str = ""
    retcode: int = 0
