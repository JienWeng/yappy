from __future__ import annotations

import os
import tempfile

import pytest

from src.storage.activity_log import ActivityLog
from src.storage.models import DailyStats


@pytest.fixture
def log() -> ActivityLog:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    activity_log = ActivityLog(db_path=db_path)
    yield activity_log
    os.unlink(db_path)


class TestActivityLog:
    def test_record_and_count_success(self, log: ActivityLog) -> None:
        log.record_comment("https://linkedin.com/post/1", "Nice work", "success")
        assert log.count_today() == 1

    def test_count_only_counts_success(self, log: ActivityLog) -> None:
        log.record_comment("https://linkedin.com/post/1", "Nice work", "success")
        log.record_comment("https://linkedin.com/post/2", "", "failed")
        assert log.count_today() == 1

    def test_was_commented_returns_true_after_success(self, log: ActivityLog) -> None:
        url = "https://linkedin.com/post/1"
        log.record_comment(url, "Nice work", "success")
        assert log.was_commented(url) is True

    def test_was_commented_returns_false_after_failure(self, log: ActivityLog) -> None:
        url = "https://linkedin.com/post/1"
        log.record_comment(url, "", "failed")
        assert log.was_commented(url) is False

    def test_was_commented_returns_false_for_unknown_url(self, log: ActivityLog) -> None:
        assert log.was_commented("https://linkedin.com/post/unknown") is False

    def test_multiple_records(self, log: ActivityLog) -> None:
        for i in range(5):
            log.record_comment(f"https://linkedin.com/post/{i}", f"comment {i}", "success")
        assert log.count_today() == 5

    def test_get_daily_stats(self, log: ActivityLog) -> None:
        log.record_comment("https://linkedin.com/post/1", "text", "success")
        log.record_comment("https://linkedin.com/post/2", "", "failed")
        log.record_comment("https://linkedin.com/post/3", "text", "success")
        stats = log.get_daily_stats()
        assert isinstance(stats, DailyStats)
        assert stats.successful == 2
        assert stats.failed == 1
        assert stats.total_attempts == 3

    def test_invalid_status_raises(self, log: ActivityLog) -> None:
        with pytest.raises(ValueError, match="Invalid status"):
            log.record_comment("https://linkedin.com/post/1", "text", "invalid")
