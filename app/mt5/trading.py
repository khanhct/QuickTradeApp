import logging
from app.mt5 import mt5_module as mt5
from app.models.trade import TradeResult

logger = logging.getLogger(__name__)


def send_market_order(symbol: str, order_type: str, lot: float,
                      sl: float = None, tp: float = None) -> TradeResult:
    """Place a market order (instant execution)."""
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return TradeResult(success=False, comment=f"Cannot get tick for {symbol}")

    if order_type == "buy":
        mt5_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
    else:
        mt5_type = mt5.ORDER_TYPE_SELL
        price = tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5_type,
        "price": price,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    if sl is not None:
        request["sl"] = sl
    if tp is not None:
        request["tp"] = tp

    result = mt5.order_send(request)
    if result is None:
        return TradeResult(success=False, comment=str(mt5.last_error()))

    success = result.retcode == mt5.TRADE_RETCODE_DONE
    if not success:
        logger.warning(f"Market order failed: {result.retcode} {result.comment}")
    return TradeResult(
        success=success,
        ticket=result.order if success else 0,
        comment=result.comment,
        retcode=result.retcode,
    )


def send_limit_order(symbol: str, order_type: str, lot: float,
                     price: float, sl: float = None, tp: float = None) -> TradeResult:
    """Place a limit/pending order."""
    if order_type == "buy":
        mt5_type = mt5.ORDER_TYPE_BUY_LIMIT
    else:
        mt5_type = mt5.ORDER_TYPE_SELL_LIMIT

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": lot,
        "type": mt5_type,
        "price": price,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    if sl is not None:
        request["sl"] = sl
    if tp is not None:
        request["tp"] = tp

    result = mt5.order_send(request)
    if result is None:
        return TradeResult(success=False, comment=str(mt5.last_error()))

    success = result.retcode == mt5.TRADE_RETCODE_DONE
    if not success:
        logger.warning(f"Limit order failed: {result.retcode} {result.comment}")
    return TradeResult(
        success=success,
        ticket=result.order if success else 0,
        comment=result.comment,
        retcode=result.retcode,
    )
