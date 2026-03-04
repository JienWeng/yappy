from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.core.rate_limiter import DailyLimitExceededError, RateLimiter, RateLimitStatus


def make_limiter(count_today: int, limit: int = 20) -> RateLimiter:
    log = MagicMock()
    log.count_today.return_value = count_today
    return RateLimiter(activity_log=log, daily_limit=limit)


class TestRateLimitStatus:
    def test_remaining_calculated_correctly(self) -> None:
        status = RateLimitStatus.from_counts(5, 20)
        assert status.remaining == 15

    def test_limit_reached_when_at_cap(self) -> None:
        status = RateLimitStatus.from_counts(20, 20)
        assert status.limit_reached is True

    def test_limit_not_reached_below_cap(self) -> None:
        status = RateLimitStatus.from_counts(19, 20)
        assert status.limit_reached is False

    def test_remaining_never_negative(self) -> None:
        status = RateLimitStatus.from_counts(25, 20)
        assert status.remaining == 0


class TestRateLimiter:
    def test_check_status_delegates_to_log(self) -> None:
        limiter = make_limiter(count_today=7, limit=20)
        status = limiter.check_status()
        assert status.comments_today == 7
        assert status.daily_limit == 20
        assert status.remaining == 13

    def test_assert_can_post_passes_below_limit(self) -> None:
        limiter = make_limiter(count_today=19, limit=20)
        limiter.assert_can_post()  # should not raise

    def test_assert_can_post_raises_at_limit(self) -> None:
        limiter = make_limiter(count_today=20, limit=20)
        with pytest.raises(DailyLimitExceededError) as exc_info:
            limiter.assert_can_post()
        assert exc_info.value.current == 20
        assert exc_info.value.limit == 20

    def test_assert_can_post_raises_above_limit(self) -> None:
        limiter = make_limiter(count_today=21, limit=20)
        with pytest.raises(DailyLimitExceededError):
            limiter.assert_can_post()

    def test_custom_limit(self) -> None:
        limiter = make_limiter(count_today=5, limit=5)
        with pytest.raises(DailyLimitExceededError):
            limiter.assert_can_post()
