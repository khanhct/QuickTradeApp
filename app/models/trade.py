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
