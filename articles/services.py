from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, Sequence

from email.utils import parsedate_to_datetime
import httpx
from django.utils import timezone

from .models import Article, RSSFeed


def _guess_published_at(published: Optional[datetime]) -> datetime:
    if published is None:
        return timezone.now()
    if timezone.is_naive(published):
        return timezone.make_aware(published, timezone=timezone.utc)
    return published


def sync_all_feeds(feed_ids: Optional[Sequence[int]] = None) -> None:
    """
    Fetch all active RSS feeds and upsert their articles.

    This is intentionally simple; performance and caching can be added later.
    """
    qs = RSSFeed.objects.filter(is_active=True)
    if feed_ids:
        qs = qs.filter(id__in=feed_ids)

    feeds: Iterable[RSSFeed] = qs

    for feed in feeds:
        # Skip if this feed already has articles; we only pull once.
        if Article.objects.filter(feed=feed).exists():
            continue
        sync_single_feed(feed)


def sync_single_feed(feed: RSSFeed) -> None:
    """
    Fetch a single RSS feed and upsert its articles.
    """
    try:
        response = httpx.get(feed.url, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError:
        return

    # Extremely lightweight RSS parsing without external dependencies.
    # Each <item> or <entry> becomes an Article.
    from xml.etree import ElementTree as ET

    root = ET.fromstring(response.text)

    # RSS 2.0: <rss><channel><item>...</item></channel></rss>
    items = root.findall(".//item")
    if not items:
        # Atom or other formats: try <entry>
        items = root.findall(".//{*}entry")

    for item in items:
        title_el = item.find("title") or item.find("{*}title")
        link_el = item.find("link") or item.find("{*}link")
        guid_el = item.find("guid") or item.find("{*}id")
        desc_el = (
            item.find("description")
            or item.find("{*}description")
            or item.find("{*}summary")
            or item.find("{*}encoded")
            or item.find("{*}content")
        )

        title = (title_el.text or "").strip() if title_el is not None else ""
        if not title:
            continue

        link = ""
        if link_el is not None:
            href = link_el.get("href")
            link = (href or link_el.text or "").strip()

        if not link:
            # Without a stable URL we skip; simplifies deduplication.
            continue

        external_id = (
            (guid_el.text or "").strip() if guid_el is not None else link
        )

        # Summary / content
        summary = ""
        if desc_el is not None:
            try:
                summary = "".join(desc_el.itertext()).strip()
            except Exception:
                summary = (desc_el.text or "").strip()

        if not summary:
            nested_desc = item.find(".//{*}description") or item.find(
                ".//{*}summary"
            )
            if nested_desc is not None and nested_desc.text:
                summary = nested_desc.text.strip()

        # Author
        author_el = (
            item.find("author")
            or item.find("{*}creator")
            or item.find("{*}author")
        )
        author = (author_el.text or "").strip() if author_el is not None else ""

        # Language – BBC and others are English; keep simple
        language = "en"

        # Published date
        published_dt: Optional[datetime] = None
        pub_el = item.find("pubDate") or item.find("{*}published")
        if pub_el is not None and pub_el.text:
            text = pub_el.text.strip()
            try:
                published_dt = parsedate_to_datetime(text)
            except (TypeError, ValueError):
                try:
                    published_dt = datetime.fromisoformat(text)
                except ValueError:
                    published_dt = None

        published_at = _guess_published_at(published_dt)

        Article.objects.update_or_create(
            feed=feed,
            external_id=external_id,
            defaults={
                "title": title[:512],
                "summary": summary,
                "content": summary,
                "url": link,
                "author": author,
                "language": language,
                "published_at": published_at,
            },
        )

    feed.last_fetched_at = timezone.now()
    feed.save(update_fields=["last_fetched_at"])

