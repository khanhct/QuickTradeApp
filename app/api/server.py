import asyncio
import logging
from concurrent.futures import Future
from typing import Optional

from fastapi import FastAPI, Depends, Query, Path

from app.api.auth import verify_token
from app.api.schemas import (
    TickResponse, PositionResponse, PendingOrderResponse,
    MarketOrderRequest, LimitOrderRequest,
    ModifySLRequest, ModifyTPRequest,
    TradeResultResponse, ConfigResponse,
)
from app.config import config
from app.core.sl_calculator import calculate_sl
from app.mt5 import mt5_module as mt5
from app.mt5 import trading, positions as positions_mod
from app.mt5.worker import MT5Worker

logger = logging.getLogger(__name__)

app = FastAPI(title="QuickTrade API", version="1.0.0")

# MT5Worker singleton — initialized by run_server.py before uvicorn starts
_worker: MT5Worker | None = None


def set_worker(worker: MT5Worker):
    global _worker
    _worker = worker


async def _run_on_worker(fn, *args, **kwargs):
    """Submit a function to the MT5Worker and await the result."""
    future: Future = _worker.submit(fn, *args, **kwargs)
    loop = asyncio.get_event_loop()
    return await asyncio.wrap_future(future, loop=loop)


# --- Tick ---

@app.get("/api/tick/{symbol}", response_model=TickResponse, dependencies=[Depends(verify_token)])
async def get_tick(symbol: str = Path(...)):
    tick = await _run_on_worker(mt5.symbol_info_tick, symbol)
    if tick is None:
        return TickResponse(bid=0, ask=0, time=0)
    return TickResponse(bid=tick.bid, ask=tick.ask, time=tick.time)


# --- Positions ---

@app.get("/api/positions", response_model=list[PositionResponse], dependencies=[Depends(verify_token)])
async def get_positions(symbol: Optional[str] = Query(None)):
    pos_list = await _run_on_worker(positions_mod.get_positions, symbol)
    return [
        PositionResponse(
            ticket=p.ticket, symbol=p.symbol, type=p.type, type_str=p.type_str,
            volume=p.volume, price_open=p.price_open, sl=p.sl, tp=p.tp,
            profit=p.profit, time=p.time, magic=p.magic, comment=p.comment,
        )
        for p in pos_list
    ]


# --- Orders ---

@app.get("/api/orders", response_model=list[PendingOrderResponse], dependencies=[Depends(verify_token)])
async def get_orders(symbol: Optional[str] = Query(None)):
    ord_list = await _run_on_worker(positions_mod.get_orders, symbol)
    return [
        PendingOrderResponse(
            ticket=o.ticket, symbol=o.symbol, type=o.type, type_str=o.type_str,
            volume=o.volume, price_open=o.price_open, sl=o.sl, tp=o.tp,
            time=o.time, magic=o.magic, comment=o.comment,
        )
        for o in ord_list
    ]


# --- Market Order ---

@app.post("/api/order/market", response_model=TradeResultResponse, dependencies=[Depends(verify_token)])
async def place_market_order(req: MarketOrderRequest):
    def _execute():
        tick = mt5.symbol_info_tick(req.symbol)
        if tick is None:
            from app.models.trade import TradeResult
            return TradeResult(success=False, comment=f"Cannot get tick for {req.symbol}")
        price = tick.ask if req.order_type == "buy" else tick.bid
        sl = req.sl
        if sl is None and req.sl_offset is not None:
            sl = calculate_sl(req.order_type, price, req.sl_offset)
        return trading.send_market_order(req.symbol, req.order_type, req.lot, sl, req.tp)

    result = await _run_on_worker(_execute)
    return TradeResultResponse(
        success=result.success, ticket=result.ticket,
        comment=result.comment, retcode=result.retcode,
    )


# --- Limit Order ---

@app.post("/api/order/limit", response_model=TradeResultResponse, dependencies=[Depends(verify_token)])
async def place_limit_order(req: LimitOrderRequest):
    sl = req.sl
    if sl is None and req.sl_offset is not None:
        sl = calculate_sl(req.order_type, req.price, req.sl_offset)

    result = await _run_on_worker(
        trading.send_limit_order, req.symbol, req.order_type, req.lot, req.price, sl, req.tp,
    )
    return TradeResultResponse(
        success=result.success, ticket=result.ticket,
        comment=result.comment, retcode=result.retcode,
    )


# --- Modify SL ---

@app.post("/api/position/{ticket}/sl", response_model=TradeResultResponse, dependencies=[Depends(verify_token)])
async def modify_sl(ticket: int, req: ModifySLRequest):
    result = await _run_on_worker(positions_mod.modify_sl, ticket, req.sl)
    return TradeResultResponse(
        success=result.success, ticket=result.ticket,
        comment=result.comment, retcode=result.retcode,
    )


# --- Modify TP ---

@app.post("/api/position/{ticket}/tp", response_model=TradeResultResponse, dependencies=[Depends(verify_token)])
async def modify_tp(ticket: int, req: ModifyTPRequest):
    result = await _run_on_worker(positions_mod.modify_tp, ticket, req.tp)
    return TradeResultResponse(
        success=result.success, ticket=result.ticket,
        comment=result.comment, retcode=result.retcode,
    )


# --- Close Position ---

@app.post("/api/position/{ticket}/close", response_model=TradeResultResponse, dependencies=[Depends(verify_token)])
async def close_position(ticket: int):
    result = await _run_on_worker(positions_mod.close_position, ticket)
    return TradeResultResponse(
        success=result.success, ticket=result.ticket,
        comment=result.comment, retcode=result.retcode,
    )


# --- Cancel Order ---

@app.post("/api/order/{ticket}/cancel", response_model=TradeResultResponse, dependencies=[Depends(verify_token)])
async def cancel_order(ticket: int):
    result = await _run_on_worker(positions_mod.cancel_order, ticket)
    return TradeResultResponse(
        success=result.success, ticket=result.ticket,
        comment=result.comment, retcode=result.retcode,
    )


# --- Config ---

@app.get("/api/config", response_model=ConfigResponse, dependencies=[Depends(verify_token)])
async def get_config():
    return ConfigResponse(
        symbols=config.symbols,
        default_symbol=config.default_symbol,
        default_lot_size=config.default_lot_size,
        default_sl_offset=config.default_sl_offset,
        sync_interval_ms=config.sync_interval_ms,
    )
