"""Book catalog endpoints: CRUD, filters, natural-key upsert, soft-delete."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import get_settings
from ..db import get_session
from ..models import Book, User
from ..schemas.book import BookCreate, BookRead, BookUpdate
from ..security.deps import require_admin, require_user
from ..security.limiter import limiter
from ..services.audit import log_audit
from ..services.catalog import upsert_book
from ..services.stock import STOCK_IN_STOCK, STOCK_LOW, STOCK_OUT, compute_stock_status

router = APIRouter(prefix="/api/books", tags=["books"])

_settings = get_settings()


def _to_read(book: Book) -> BookRead:
    return BookRead(
        id=book.id,
        title=book.title,
        author=book.author,
        editorial=book.editorial,
        category_id=book.category_id,
        category_name=book.category.name if book.category is not None else None,
        price=book.price,
        stock=book.stock,
        isbn=book.isbn,
        genre=book.genre,
        source_sheet=book.source_sheet,
        is_active=book.is_active,
        stock_status=compute_stock_status(book.stock, _settings.low_stock_threshold),
    )


def _stock_status_condition(stock_status: str):
    threshold = _settings.low_stock_threshold
    if stock_status == STOCK_IN_STOCK:
        return Book.stock > threshold
    if stock_status == STOCK_LOW:
        return and_(Book.stock > 0, Book.stock <= threshold)
    if stock_status == STOCK_OUT:
        return Book.stock == 0
    return None


@router.get("", response_model=list[BookRead])
@limiter.limit(_settings.rate_limit_api)
async def list_books(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
    q: str | None = None,
    category_id: int | None = None,
    stock_status: str | None = None,
    author: str | None = None,
    editorial: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> list[BookRead]:
    query = (
        select(Book)
        .options(selectinload(Book.category))
        .where(Book.is_active.is_(True))
    )
    if q:
        like = f"%{q.lower()}%"
        query = query.where(
            or_(
                func.lower(Book.title).like(like),
                func.lower(Book.author).like(like),
                func.lower(Book.editorial).like(like),
            )
        )
    if category_id is not None:
        query = query.where(Book.category_id == category_id)
    if author:
        query = query.where(func.lower(Book.author).like(f"%{author.lower()}%"))
    if editorial:
        query = query.where(func.lower(Book.editorial).like(f"%{editorial.lower()}%"))
    if stock_status:
        condition = _stock_status_condition(stock_status)
        if condition is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid stock_status: {stock_status!r}; expected "
                    f"{STOCK_IN_STOCK!r}, {STOCK_LOW!r}, or {STOCK_OUT!r}"
                ),
            )
        query = query.where(condition)

    query = (
        query.order_by(Book.title)
        .offset(max(0, page - 1) * page_size)
        .limit(page_size)
    )
    books = (await session.execute(query)).scalars().all()
    return [_to_read(book) for book in books]


@router.get("/{book_id}", response_model=BookRead)
@limiter.limit(_settings.rate_limit_api)
async def get_book(
    request: Request,
    book_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
) -> BookRead:
    book = (
        await session.execute(
            select(Book)
            .options(selectinload(Book.category))
            .where(Book.id == book_id, Book.is_active.is_(True))
        )
    ).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return _to_read(book)


@router.post("", response_model=BookRead)
@limiter.limit(_settings.rate_limit_api)
async def create_book(
    request: Request,
    response: Response,
    body: BookCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
) -> BookRead:
    book, created = await upsert_book(
        session,
        title=body.title,
        author=body.author,
        editorial=body.editorial,
        category_id=body.category_id,
        price=body.price,
        stock=body.stock,
        isbn=body.isbn,
        genre=body.genre,
    )
    await log_audit(
        session,
        user_id=user.id,
        entity_type="book",
        entity_id=book.id,
        action="create" if created else "update",
        changes={
            "title": book.title,
            "author": book.author,
            "editorial": book.editorial,
            "category_id": book.category_id,
            "price": str(book.price),
            "stock": book.stock,
        },
    )
    await session.commit()

    book = (
        await session.execute(
            select(Book)
            .options(selectinload(Book.category))
            .where(Book.id == book.id)
        )
    ).scalar_one()
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return _to_read(book)


@router.put("/{book_id}", response_model=BookRead)
@limiter.limit(_settings.rate_limit_api)
async def update_book(
    request: Request,
    book_id: int,
    body: BookUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
) -> BookRead:
    book = (
        await session.execute(
            select(Book).options(selectinload(Book.category)).where(Book.id == book_id)
        )
    ).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    data = body.model_dump(exclude_unset=True)
    changes: dict = {}
    for field, value in data.items():
        old = getattr(book, field)
        if old != value:
            changes[field] = {"old": str(old), "new": str(value)}
            setattr(book, field, value)

    if changes:
        await log_audit(
            session,
            user_id=user.id,
            entity_type="book",
            entity_id=book.id,
            action="update",
            changes=changes,
        )
    await session.commit()
    return _to_read(book)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(_settings.rate_limit_api)
async def delete_book(
    request: Request,
    book_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[User, Depends(require_admin)],
) -> Response:
    book = (
        await session.execute(select(Book).where(Book.id == book_id))
    ).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    book.is_active = False
    await log_audit(
        session,
        user_id=admin.id,
        entity_type="book",
        entity_id=book.id,
        action="delete",
        changes={"is_active": False},
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
