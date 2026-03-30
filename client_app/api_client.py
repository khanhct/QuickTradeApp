"""HTTP client that wraps all QuickTrade API calls."""
import logging
from typing import Optional

import requests

from app.models.trade import Position, PendingOrder, TradeResult

logger = logging.getLogger(__name__)


class ApiClient:
    def __init__(self, base_url: str, token: str):
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {token}"

    def _get(self, path: str, params: dict = None):
        resp = self._session.get(f"{self._base_url}{path}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json: dict = None):
        resp = self._session.post(f"{self._base_url}{path}", json=json, timeout=10)
        resp.raise_for_status()
        return resp.json()

    # --- Tick ---

    def get_tick(self, symbol: str):
        """Returns dict with bid, ask, time."""
        return self._get(f"/api/tick/{symbol}")

    # --- Positions ---

    def get_positions(self, symbol: Optional[str] = None) -> list[Position]:
        params = {"symbol": symbol} if symbol else None
        data = self._get("/api/positions", params=params)
        return [
            Position(
                ticket=p["ticket"], symbol=p["symbol"], type=p["type"],
                volume=p["volume"], price_open=p["price_open"],
                sl=p["sl"], tp=p["tp"], profit=p["profit"],
                time=p["time"], magic=p.get("magic", 0), comment=p.get("comment", ""),
            )
            for p in data
        ]

    # --- Orders ---

    def get_orders(self, symbol: Optional[str] = None) -> list[PendingOrder]:
        params = {"symbol": symbol} if symbol else None
        data = self._get("/api/orders", params=params)
        return [
            PendingOrder(
                ticket=o["ticket"], symbol=o["symbol"], type=o["type"],
                volume=o["volume"], price_open=o["price_open"],
                sl=o["sl"], tp=o["tp"], time=o["time"],
                magic=o.get("magic", 0), comment=o.get("comment", ""),
            )
            for o in data
        ]

    # --- Market Order ---

    def send_market_order(self, symbol: str, order_type: str, lot: float,
                          sl: float = None, tp: float = None,
                          sl_offset: float = None) -> TradeResult:
        body = {"symbol": symbol, "order_type": order_type, "lot": lot}
        if sl is not None:
            body["sl"] = sl
        if tp is not None:
            body["tp"] = tp
        if sl_offset is not None:
            body["sl_offset"] = sl_offset
        data = self._post("/api/order/market", json=body)
        return TradeResult(**data)

    # --- Limit Order ---

    def send_limit_order(self, symbol: str, order_type: str, lot: float,
                         price: float, sl: float = None, tp: float = None,
                         sl_offset: float = None) -> TradeResult:
        body = {"symbol": symbol, "order_type": order_type, "lot": lot, "price": price}
        if sl is not None:
            body["sl"] = sl
        if tp is not None:
            body["tp"] = tp
        if sl_offset is not None:
            body["sl_offset"] = sl_offset
        data = self._post("/api/order/limit", json=body)
        return TradeResult(**data)

    # --- Modify SL/TP ---

    def modify_sl(self, ticket: int, sl: float) -> TradeResult:
        data = self._post(f"/api/position/{ticket}/sl", json={"sl": sl})
        return TradeResult(**data)

    def modify_tp(self, ticket: int, tp: float) -> TradeResult:
        data = self._post(f"/api/position/{ticket}/tp", json={"tp": tp})
        return TradeResult(**data)

    # --- Close / Cancel ---

    def close_position(self, ticket: int) -> TradeResult:
        data = self._post(f"/api/position/{ticket}/close")
        return TradeResult(**data)

    def cancel_order(self, ticket: int) -> TradeResult:
        data = self._post(f"/api/order/{ticket}/cancel")
        return TradeResult(**data)

    # --- Config ---

    def get_config(self) -> dict:
        return self._get("/api/config")
