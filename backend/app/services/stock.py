"""Stock status (badge) computation."""

STOCK_IN_STOCK = "In Stock"
STOCK_LOW = "Low"
STOCK_OUT = "Out"


def compute_stock_status(stock: int, threshold: int) -> str:
    """Derive the stock badge from stock level vs threshold.

    ``stock == 0`` → Out · ``0 < stock <= threshold`` → Low ·
    ``stock > threshold`` → In Stock.
    """
    if stock <= 0:
        return STOCK_OUT
    if stock <= threshold:
        return STOCK_LOW
    return STOCK_IN_STOCK
