from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.config import TargetConfig
from src.scraper.linkedin_scraper import LinkedInScraper

# --- Mock HTML Snippets ---

OLD_DESIGN_HTML = """
<div class="feed-shared-update-v2" data-urn="activity:12345">
    <span class="feed-shared-update-v2__author-name">Old Author</span>
    <div class="feed-shared-update-v2__description">
        <span class="break-words">This is an old design post.</span>
    </div>
    <a href="/feed/update/activity:12345/">Link</a>
</div>
<div class="feed-shared-update-v2" data-urn="activity:67890">
    <span class="feed-shared-update-v2__author-name">Another Old Author</span>
    <div class="feed-shared-update-v2__description">
        <span class="break-words">Another old post.</span>
    </div>
</div>
"""

NEW_DESIGN_HTML = """
<div data-view-name="feed-full-update" data-urn="activity:99999">
    <span class="update-components-actor__name">New Author</span>
    <div class="update-components-text">
        <span class="break-words">This is a new design post.</span>
    </div>
    <a href="/feed/update/activity:99999/">Link</a>
</div>
<div data-view-name="feed-full-update" data-urn="activity:88888">
    <span class="update-components-actor__name">Second New Author</span>
    <div class="update-components-text">
        <span class="break-words">Second new post.</span>
    </div>
</div>
"""

@pytest.fixture
def mock_log():
    m = MagicMock()
    m.was_commented.return_value = False
    return m

@pytest.mark.asyncio
async def test_scraper_finds_old_design_posts(mock_log):
    page = AsyncMock()
    scraper = LinkedInScraper(
        context=MagicMock(),
        activity_log=mock_log,
        min_reactions=0,
        min_comments=0
    )

    c1 = AsyncMock()
    c1.get_attribute = AsyncMock(side_effect=lambda attr: "activity:12345" if attr == "data-urn" else None)

    text_el = AsyncMock()
    text_el.inner_text = AsyncMock(return_value="This is a very long post text that should definitely pass the media-only check because it has more than eighty characters in total and provides enough context for the AI to generate a meaningful comment.")

    author_el = AsyncMock()
    author_el.inner_text = AsyncMock(return_value="Old Author")

    async def dynamic_selector(sel):
        if "description" in sel or "break-words" in sel: return text_el
        if "author-name" in sel or "actor__name" in sel: return author_el
        return None
    c1.query_selector = AsyncMock(side_effect=dynamic_selector)

    page.query_selector_all = AsyncMock(return_value=[c1])

    target = TargetConfig(type="feed", value="", max_posts=1)
    posts = await scraper._extract_posts_from_page(page, target)

    assert len(posts) == 1
    assert posts[0].author_name == "Old Author"

@pytest.mark.asyncio
async def test_scraper_finds_new_design_posts(mock_log):
    page = AsyncMock()
    scraper = LinkedInScraper(
        context=MagicMock(),
        activity_log=mock_log,
        min_reactions=0,
        min_comments=0
    )

    c1 = AsyncMock()
    c1.get_attribute = AsyncMock(side_effect=lambda attr: "activity:99999" if attr == "data-urn" else None)

    text_el = AsyncMock()
    text_el.inner_text = AsyncMock(return_value="Here is another very long post for the new design testing. It also has more than eighty characters to ensure that the scraper doesn't skip it as a media-only post. Testing robustness is key!")

    author_el = AsyncMock()
    author_el.inner_text = AsyncMock(return_value="New Author")

    async def dynamic_selector(sel):
        if "update-components-text" in sel or "break-words" in sel: return text_el
        if "actor__name" in sel: return author_el
        return None
    c1.query_selector = AsyncMock(side_effect=dynamic_selector)

    page.query_selector_all = AsyncMock(return_value=[c1])

    target = TargetConfig(type="feed", value="", max_posts=1)
    posts = await scraper._extract_posts_from_page(page, target)

    assert len(posts) == 1
    assert posts[0].author_name == "New Author"
