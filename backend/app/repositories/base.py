from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from sqlalchemy import Select
from sqlalchemy.orm import Session

from app.core.exceptions import PharmaQSentinelError

ModelT = TypeVar("ModelT")


class RepositoryNotFoundError(PharmaQSentinelError):
    def __init__(self, entity_name: str, lookup: str) -> None:
        super().__init__(f"{entity_name} not found: {lookup}", status_code=404)


@dataclass(frozen=True)
class Pagination:
    limit: int = 50
    offset: int = 0

    def __post_init__(self) -> None:
        if self.limit < 1 or self.limit > 200:
            raise ValueError("limit must be between 1 and 200")
        if self.offset < 0:
            raise ValueError("offset must be zero or greater")


class BaseRepository(Generic[ModelT]):
    entity_name = "Record"

    def __init__(self, db: Session) -> None:
        self.db = db

    def require(self, value: ModelT | None, lookup: str) -> ModelT:
        if value is None:
            raise RepositoryNotFoundError(self.entity_name, lookup)
        return value


def apply_pagination(statement: Select[tuple[ModelT]], pagination: Pagination) -> Select[tuple[ModelT]]:
    return statement.limit(pagination.limit).offset(pagination.offset)
