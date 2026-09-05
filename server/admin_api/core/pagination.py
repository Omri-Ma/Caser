from typing import Generic, List, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy.orm import Query as SAQuery

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

T = TypeVar("T")


class PageParams:
    """Shared query params for every list endpoint in this app — 50/page by
    default, capped at 200 so a request can't ask for everything in one shot.
    """

    def __init__(self, page: int = Query(1, ge=1), page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)):
        self.page = page
        self.page_size = page_size


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int


def paginate(query: SAQuery, params: PageParams) -> tuple[list, int]:
    total = query.count()
    items = query.offset((params.page - 1) * params.page_size).limit(params.page_size).all()
    return items, total
