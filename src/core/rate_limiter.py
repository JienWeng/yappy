from __future__ import annotations

from dataclasses import dataclass


class DailyLimitExceededError(Exception):
    """Raised when the daily comment limit has been reached."""

    def __init__(self, current: int, limit: int) -> None:
        self.current = current
        self.limit = limit
        super().__init__(
            f"Daily comment limit reached: {current}/{limit}. "
            "Try again tomorrow."
        )


@dataclass(frozen=True)
class RateLimitStatus:
    comments_today: int
    daily_limit: int
    remaining: int
    limit_reached: bool

    @classmethod
    def from_counts(cls, comments_today: int, daily_limit: int) -> "RateLimitStatus":
        remaining = max(0, daily_limit - comments_today)
        return cls(
            comments_today=comments_today,
            daily_limit=daily_limit,
            remaining=remaining,
            limit_reached=remaining == 0,
        )


class RateLimiter:
    """Enforces the daily comment limit by delegating reads to ActivityLog."""

    def __init__(self, activity_log: object, daily_limit: int) -> None:
        self._log = activity_log
        self._daily_limit = daily_limit

    def check_status(self) -> RateLimitStatus:
        count = self._log.count_today()
        return RateLimitStatus.from_counts(count, self._daily_limit)

    def assert_can_post(self) -> None:
        """Raise DailyLimitExceededError if the limit has been reached."""
        status = self.check_status()
        if status.limit_reached:
            raise DailyLimitExceededError(status.comments_today, self._daily_limit)
