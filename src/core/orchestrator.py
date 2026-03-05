from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.core.callbacks import NullCallbacks

if TYPE_CHECKING:
    from src.core.callbacks import OrchestratorCallbacks
    from src.core.config import AppConfig
    from src.core.rate_limiter import RateLimiter
    from src.scraper.linkedin_scraper import LinkedInScraper
    from src.ai.comment_generator import CommentGenerator
    from src.executor.comment_poster import CommentPoster
    from src.storage.activity_log import ActivityLog

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    started_at: datetime
    finished_at: datetime
    posts_scraped: int
    comments_attempted: int
    comments_succeeded: int
    comments_failed: int
    errors: tuple[str, ...]


class Orchestrator:
    def __init__(
        self,
        config: "AppConfig",
        rate_limiter: "RateLimiter",
        scraper: "LinkedInScraper",
        comment_generator: "CommentGenerator",
        comment_poster: "CommentPoster",
        activity_log: "ActivityLog",
        callbacks: "OrchestratorCallbacks | None" = None,
    ) -> None:
        self._config = config
        self._rate_limiter = rate_limiter
        self._scraper = scraper
        self._generator = comment_generator
        self._poster = comment_poster
        self._log = activity_log
        self._callbacks: OrchestratorCallbacks = callbacks or NullCallbacks()

    async def run(self) -> PipelineResult:
        started_at = datetime.now(timezone.utc)
        posts_scraped = 0
        comments_attempted = 0
        comments_succeeded = 0
        comments_failed = 0
        errors: list[str] = []

        for target in self._config.targets:
            logger.info("Processing target: %s=%s", target.type, target.value)
            try:
                scrape_result = await self._scraper.scrape_target(target)
            except Exception as exc:
                error_msg = f"Scrape failed for target {target.value!r}: {exc}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue

            posts_scraped += len(scrape_result.posts)
            logger.info("Scraped %d posts from target %r", len(scrape_result.posts), target.value)

            for post in scrape_result.posts:
                if self._callbacks.should_stop():
                    break
                while self._callbacks.should_pause():
                    await asyncio.sleep(0.5)

                self._callbacks.on_post_found(
                    post_url=post.post_url,
                    author_name=post.author_name,
                    text_preview=post.post_text[:100],
                )

                try:
                    self._rate_limiter.assert_can_post()
                except Exception as exc:
                    logger.warning("Rate limit: %s — stopping pipeline", exc)
                    errors.append(str(exc))
                    return PipelineResult(
                        started_at=started_at,
                        finished_at=datetime.now(timezone.utc),
                        posts_scraped=posts_scraped,
                        comments_attempted=comments_attempted,
                        comments_succeeded=comments_succeeded,
                        comments_failed=comments_failed,
                        errors=tuple(errors),
                    )

                comments_attempted += 1
                try:
                    # Fetch real existing comments to ground the generation
                    existing = await self._scraper.fetch_comments(post.post_url, limit=4)
                    if existing:
                        logger.debug("Enriching post with %d existing comments", len(existing))
                        post = replace(post, existing_comments=tuple(existing))

                    generate_result = self._generator.generate(post)
                    if generate_result.error:
                        raise RuntimeError(f"Generation failed: {generate_result.error}")

                    self._callbacks.on_comment_generated(
                        post_url=post.post_url,
                        author_name=post.author_name,
                        comment_text=generate_result.comment.text,
                    )

                    # Manual approval check
                    decision, final_text = self._callbacks.on_awaiting_approval(
                        post_url=post.post_url,
                        author_name=post.author_name,
                        post_preview=post.post_text[:100],
                        comment_text=generate_result.comment.text,
                    )

                    if decision == "skip":
                        logger.info("Comment skipped by user for %s", post.post_url)
                        continue
                    elif decision == "regenerate":
                        generate_result = self._generator.generate(post)
                        if generate_result.error:
                            raise RuntimeError(f"Regeneration failed: {generate_result.error}")
                        final_text = generate_result.comment.text

                    final_comment = replace(generate_result.comment, text=final_text)

                    post_result = await self._poster.post_comment(
                        post, final_comment
                    )
                    if post_result.success:
                        self._log.record_comment(
                            post_url=post.post_url,
                            comment_text=final_comment.text,
                            status="success",
                        )
                        comments_succeeded += 1
                        self._callbacks.on_comment_posted(
                            post_url=post.post_url,
                            comment_text=final_comment.text,
                        )
                        logger.info(
                            "Comment posted on %s (liked=%s)",
                            post.post_url, post_result.liked,
                        )
                    else:
                        raise RuntimeError(f"Post failed: {post_result.error}")

                except Exception as exc:
                    error_msg = f"Failed on post {post.post_url!r}: {exc}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    comments_failed += 1
                    self._callbacks.on_comment_failed(
                        post_url=post.post_url, error=str(exc),
                    )
                    self._log.record_comment(
                        post_url=post.post_url,
                        comment_text="",
                        status="failed",
                    )

                status = self._rate_limiter.check_status()
                self._callbacks.on_stats_updated(
                    comments_today=status.comments_today,
                    daily_limit=status.daily_limit,
                    posts_scanned=posts_scraped,
                    posts_skipped=posts_scraped - comments_attempted,
                    success_count=comments_succeeded,
                    fail_count=comments_failed,
                )

                await self._random_delay()

        return PipelineResult(
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            posts_scraped=posts_scraped,
            comments_attempted=comments_attempted,
            comments_succeeded=comments_succeeded,
            comments_failed=comments_failed,
            errors=tuple(errors),
        )

    async def _random_delay(self) -> None:
        delay = random.uniform(
            self._config.limits.min_delay_seconds,
            self._config.limits.max_delay_seconds,
        )
        logger.debug("Waiting %.1f seconds before next action", delay)
        await asyncio.sleep(delay)
