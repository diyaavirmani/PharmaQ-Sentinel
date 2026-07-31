from __future__ import annotations

import random
from dataclasses import dataclass

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 4.0
    jitter_seconds: float = 0.1

    def should_retry(self, exc: BaseException) -> bool:
        if isinstance(exc, (AuthenticationError, BadRequestError, NotFoundError, PermissionDeniedError)):
            return False
        if isinstance(exc, (APITimeoutError, APIConnectionError, RateLimitError)):
            return True
        if isinstance(exc, APIStatusError):
            return exc.status_code >= 500
        return False

    def delay_seconds(self, retry_number: int) -> float:
        exponential_delay = self.base_delay_seconds * (2 ** max(retry_number - 1, 0))
        bounded_delay = min(exponential_delay, self.max_delay_seconds)
        return bounded_delay + random.uniform(0, self.jitter_seconds)
