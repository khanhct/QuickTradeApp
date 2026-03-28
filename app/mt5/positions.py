import logging
from typing import Optional
from app.mt5 import mt5_module as mt5
from app.models.trade import Position, TradeResult

logger = logging.getLogger(__name__)


def get_positions(symbol: Optional[str] = None) -> list[Position]:
    """Get all open positions, optionally filtered by symbol."""
    if symbol:
        raw = mt5.positions_get(symbol=symbol)
    else:
        raw = mt5.positions_get()

    if raw is None:
        logger.warning(f"Failed to get positions: {mt5.last_error()}")
        return []

    positions = []
    for p in raw:
        positions.append(Position(
            ticket=p.ticket,
            symbol=p.symbol,
            type=p.type,
            volume=p.volume,
            price_open=p.price_open,
            sl=p.sl,
            tp=p.tp,
            profit=p.profit,
            time=p.time,
            magic=p.magic,
            comment=p.comment,
        ))
    return positions


def modify_sl(ticket: int, new_sl: float) -> TradeResult:
    """Modify stop loss of an open position."""
    pos = mt5.positions_get(ticket=ticket)
    if not pos:
        return TradeResult(success=False, comment=f"Position {ticket} not found")

    pos = pos[0]
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "symbol": pos.symbol,
        "sl": new_sl,
        "tp": pos.tp,
    }
    result = mt5.order_send(request)
    if result is None:
        return TradeResult(success=False, comment=str(mt5.last_error()))

    success = result.retcode == mt5.TRADE_RETCODE_DONE
    if not success:
        logger.warning(f"modify_sl {ticket} failed: {result.retcode} {result.comment}")
    return TradeResult(
        success=success,
        ticket=ticket,
        comment=result.comment,
        retcode=result.retcode,
    )


def close_position(ticket: int) -> TradeResult:
    """Close an open position by placing an opposite market order."""
    pos = mt5.positions_get(ticket=ticket)
    if not pos:
        return TradeResult(success=False, comment=f"Position {ticket} not found")

    pos = pos[0]
    # Opposite direction
    if pos.type == mt5.ORDER_TYPE_BUY:
        trade_type = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(pos.symbol).bid
    else:
        trade_type = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(pos.symbol).ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": pos.symbol,
        "volume": pos.volume,
        "type": trade_type,
        "price": price,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None:
        return TradeResult(success=False, comment=str(mt5.last_error()))

    success = result.retcode == mt5.TRADE_RETCODE_DONE
    if not success:
        logger.warning(f"close_position {ticket} failed: {result.retcode} {result.comment}")
    return TradeResult(
        success=success,
        ticket=result.order if success else 0,
        comment=result.comment,
        retcode=result.retcode,
    )
