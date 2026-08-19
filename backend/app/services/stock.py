"""Stock status (badge) computation."""

STOCK_IN_STOCK = "In Stock"
STOCK_LOW = "Low"
STOCK_OUT = "Out"


def compute_stock_status(stock: int, threshold: int) -> str:
    """Derive the stock badge from the stock level (binary states only).

    ``stock <= 0`` → Out · ``stock > 0`` → In Stock.

    The ``threshold`` parameter is retained for call-site compatibility but is
    **deprecated/unused**: the low-stock tier no longer exists, so it never
    influences the result. :data:`STOCK_LOW` is kept exported for
    compatibility but is never emitted by this function.
    """
    if stock <= 0:
        return STOCK_OUT
    return STOCK_IN_STOCK
