from pydantic import BaseModel
from typing import Optional


class TickResponse(BaseModel):
    bid: float
    ask: float
    time: int


class PositionResponse(BaseModel):
    ticket: int
    symbol: str
    type: int
    type_str: str
    volume: float
    price_open: float
    sl: float
    tp: float
    profit: float
    time: int
    magic: int = 0
    comment: str = ""


class PendingOrderResponse(BaseModel):
    ticket: int
    symbol: str
    type: int
    type_str: str
    volume: float
    price_open: float
    sl: float
    tp: float
    time: int
    magic: int = 0
    comment: str = ""


class MarketOrderRequest(BaseModel):
    symbol: str
    order_type: str  # "buy" or "sell"
    lot: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    sl_offset: Optional[float] = None


class LimitOrderRequest(BaseModel):
    symbol: str
    order_type: str  # "buy" or "sell"
    lot: float
    price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    sl_offset: Optional[float] = None


class ModifySLRequest(BaseModel):
    sl: float


class ModifyTPRequest(BaseModel):
    tp: float


class TradeResultResponse(BaseModel):
    success: bool
    ticket: int = 0
    comment: str = ""
    retcode: int = 0


class ConfigResponse(BaseModel):
    symbols: list[str]
    default_symbol: str
    default_lot_size: float
    default_sl_offset: float
    sync_interval_ms: int
