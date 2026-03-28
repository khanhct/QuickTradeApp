def calculate_sl(order_type: str, price: float, offset: float) -> float:
    """Calculate stop loss from price and offset.

    Buy: SL = price - offset
    Sell: SL = price + offset
    """
    if order_type == "buy":
        return round(price - offset, 5)
    else:
        return round(price + offset, 5)
