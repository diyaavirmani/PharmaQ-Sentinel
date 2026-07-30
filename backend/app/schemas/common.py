from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer


def serialise_decimal(value: Decimal) -> str:
    return format(value, "f")


def serialise_utc_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        utc_value = value.replace(tzinfo=UTC)
    else:
        utc_value = value.astimezone(UTC)
    return utc_value.isoformat().replace("+00:00", "Z")


DecimalString = Annotated[
    Decimal,
    PlainSerializer(serialise_decimal, return_type=str, when_used="json"),
]

UTCDateTime = Annotated[
    datetime,
    PlainSerializer(serialise_utc_datetime, return_type=str, when_used="json"),
]
