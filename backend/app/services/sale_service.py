"""Sales POS service: atomic stock decrement, oversell guard, price snapshot.

Full sale transaction (REQ-POS-1..4, design D8):
numbering -> per-item atomic decrement -> price snapshot -> insert sale+items
-> audit. Any oversell raises :class:`OversellError`; the caller rolls back the
whole transaction (all-or-nothing, no partial decrement).
"""

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Book, Sale, SaleItem, User
from ..schemas.sale import SaleItemCreate
from .audit import log_audit
from .numbering import next_sale_number


class SaleError(Exception):
    """Base class for sale-domain errors mapped to HTTP responses."""


class OversellError(SaleError):
    def __init__(self, book_id: int):
        self.book_id = book_id
        super().__init__(
            f"Cannot sell more than available stock for book {book_id}"
        )


class BookUnavailableError(SaleError):
    def __init__(self, book_id: int):
        self.book_id = book_id
        super().__init__(f"Book {book_id} not found or inactive")


async def create_sale(
    session: AsyncSession,
    *,
    cashier: User,
    items: list[SaleItemCreate],
    seller: str,
    payment_method: str | None = None,
    customer_name: str | None = None,
    customer_cuit: str | None = None,
) -> Sale:
    """Create a sale with items inside ONE transaction (caller commits).

    Raises ``OversellError`` if any item's stock cannot cover the requested
    quantity, or ``BookUnavailableError`` for a missing/inactive book.
    """
    sale_number = await next_sale_number(session)

    sale = Sale(
        sale_number=sale_number,
        total=Decimal("0.00"),
        seller=seller,
        payment_method=payment_method,
        customer_name=customer_name,
        customer_cuit=customer_cuit,
        created_by=cashier.id,
    )
    session.add(sale)
    await session.flush()

    total = Decimal("0.00")
    for item in items:
        book = (
            await session.execute(
                select(Book).where(
                    Book.id == item.book_id, Book.is_active.is_(True)
                )
            )
        ).scalar_one_or_none()
        if book is None:
            raise BookUnavailableError(item.book_id)

        # Atomic decrement with oversell guard (REQ-POS-1, REQ-POS-2).
        result = await session.execute(
            update(Book)
            .where(Book.id == item.book_id, Book.stock >= item.quantity)
            .values(stock=Book.stock - item.quantity)
        )
        if result.rowcount != 1:
            raise OversellError(item.book_id)

        # Price snapshot: FOR UPDATE read under the same transaction (REQ-POS-4).
        price = (
            await session.execute(
                select(Book.price)
                .where(Book.id == item.book_id)
                .with_for_update()
            )
        ).scalar_one()
        subtotal = (price * item.quantity).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total += subtotal

        session.add(
            SaleItem(
                sale_id=sale.id,
                book_id=item.book_id,
                quantity=item.quantity,
                unit_price=price,
                subtotal=subtotal,
            )
        )

    sale.total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    await log_audit(
        session,
        user_id=cashier.id,
        entity_type="sale",
        entity_id=sale.id,
        action="create",
        changes={
            "sale_number": sale.sale_number,
            "total": str(sale.total),
            "seller": seller,
            "items": len(items),
        },
    )
    return sale