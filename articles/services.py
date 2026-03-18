from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, Sequence

from email.utils import parsedate_to_datetime
import httpx
from django.utils import timezone
from urllib.parse import urlparse
from html.parser import HTMLParser

from .models import Article, RSSFeed


def _guess_published_at(published: Optional[datetime]) -> datetime:
    if published is None:
        return timezone.now()
    if timezone.is_naive(published):
        return timezone.make_aware(published, timezone=timezone.utc)
    return published


def sync_all_feeds(
    feed_ids: Optional[Sequence[int]] = None,
    categories: Optional[Sequence[str]] = None,
) -> None:
    """
    Fetch all active RSS feeds and upsert their articles.

    This is intentionally simple; performance and caching can be added later.
    """
    qs = RSSFeed.objects.filter(is_active=True)
    if feed_ids:
        qs = qs.filter(id__in=feed_ids)
    if categories:
        qs = qs.filter(category__in=categories)

    feeds: Iterable[RSSFeed] = qs

    for feed in feeds:
        sync_single_feed(feed)


def _strip(s: Optional[str]) -> str:
    return (s or "").strip()


def _localname(tag: str) -> str:
    # "{namespace}tag" -> "tag"
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _find_first_child(item, *names: str):
    """
    Find direct child by localname or exact tag, namespace-agnostic.
    """
    wanted = set(names)
    for child in list(item):
        ln = _localname(child.tag)
        if ln in wanted or child.tag in wanted:
            return child
    return None


def _find_all_children(item, name: str):
    """
    Find direct children matching localname, namespace-agnostic.
    """
    out = []
    for child in list(item):
        if _localname(child.tag) == name:
            out.append(child)
    return out


def _text(el) -> str:
    if el is None:
        return ""
    try:
        # Includes CDATA and nested nodes
        return "".join(el.itertext()).strip()
    except Exception:
        return _strip(getattr(el, "text", ""))


def _extract_link(item) -> str:
    # RSS: <link>text</link>
    # Atom: <link href="..."/>
    link_el = _find_first_child(item, "link")
    if link_el is None:
        return ""
    href = link_el.get("href")
    return _strip(href) or _text(link_el)


def _extract_guid(item, fallback: str) -> str:
    guid_el = _find_first_child(item, "guid", "id")
    guid = _text(guid_el)
    return guid or fallback


def _extract_author_generic(item) -> str:
    # Common patterns: <author>, <dc:creator>, Atom <author><name>...</name></author>
    author_el = _find_first_child(item, "author", "creator")
    if author_el is None:
        return ""
    # Atom author often has <name>
    name_el = None
    for child in list(author_el):
        if _localname(child.tag) == "name":
            name_el = child
            break
    return _text(name_el) or _text(author_el)


def _extract_summary_content_rss(item) -> tuple[str, str]:
    """
    RSS-heavy extraction with common extensions:
    - description
    - content:encoded
    - itunes:summary (podcasts)
    """
    description_el = _find_first_child(item, "description")
    encoded_el = _find_first_child(item, "encoded")  # content:encoded localname
    itunes_summary_el = _find_first_child(item, "summary")  # itunes:summary localname

    description = _text(description_el)
    encoded = _text(encoded_el)
    itunes_summary = _text(itunes_summary_el)

    summary = description or itunes_summary or encoded
    content = encoded or description or itunes_summary
    return summary, content


def _extract_summary_content_atom(item) -> tuple[str, str]:
    summary_el = _find_first_child(item, "summary")
    content_el = _find_first_child(item, "content")
    summary = _text(summary_el)
    content = _text(content_el) or summary
    return summary, content


def _parse_bbc_sport(item) -> dict:
    # BBC RSS: description is the snippet; author typically not provided per-item
    title = _text(_find_first_child(item, "title"))
    link = _extract_link(item)
    summary, content = _extract_summary_content_rss(item)
    return {
        "title": title,
        "link": link,
        "summary": summary,
        "content": content,
        "author": _extract_author_generic(item),
        "image_url": _extract_image_from_xml(item),
        "language": "en-gb",
    }


def _parse_cnn(item) -> dict:
    # CNN RSS: description is the snippet; author rarely present
    title = _text(_find_first_child(item, "title"))
    link = _extract_link(item)
    summary, content = _extract_summary_content_rss(item)
    return {
        "title": title,
        "link": link,
        "summary": summary,
        "content": content,
        "author": _extract_author_generic(item),
        "image_url": _extract_image_from_xml(item),
        "language": "en",
    }


def _parse_simplecast(item) -> dict:
    # Podcast feeds: prefer itunes:summary, and content:encoded when present
    title = _text(_find_first_child(item, "title"))
    link = _extract_link(item)
    summary, content = _extract_summary_content_rss(item)
    # Some podcast feeds put text in <subtitle> or <summary> (itunes), already covered
    return {
        "title": title,
        "link": link,
        "summary": summary,
        "content": content,
        "author": _extract_author_generic(item),
        "image_url": _extract_image_from_xml(item),
        "language": "en",
    }


def _parse_openai_atom(item) -> dict:
    # OpenAI is Atom: <entry><title>, <link href>, <summary>/<content>, <author><name>
    title = _text(_find_first_child(item, "title"))
    link = _extract_link(item)
    summary, content = _extract_summary_content_atom(item)
    author = _extract_author_generic(item)
    return {
        "title": title,
        "link": link,
        "summary": summary,
        "content": content,
        "author": author,
        "image_url": _extract_image_from_xml(item),
        "language": "en",
    }


def _parse_openai_rss(item) -> dict:
    # OpenAI currently serves RSS2 with <description>
    title = _text(_find_first_child(item, "title"))
    link = _extract_link(item)
    summary, content = _extract_summary_content_rss(item)
    author = _extract_author_generic(item)
    return {
        "title": title,
        "link": link,
        "summary": summary,
        "content": content,
        "author": author,
        "image_url": _extract_image_from_xml(item),
        "language": "en",
    }


class _MetaExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.description: str = ""
        self.og_description: str = ""
        self.og_image: str = ""
        self.twitter_image: str = ""
        self.author: str = ""

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta":
            return
        d = {k.lower(): (v or "") for k, v in attrs if k}
        content = d.get("content", "").strip()
        if not content:
            return

        name = d.get("name", "").lower()
        prop = d.get("property", "").lower()

        if name == "description" and not self.description:
            self.description = content
        if prop == "og:description" and not self.og_description:
            self.og_description = content
        if prop == "og:image" and not self.og_image:
            self.og_image = content
        if name == "twitter:image" and not self.twitter_image:
            self.twitter_image = content
        if name == "author" and not self.author:
            self.author = content


def _enrich_from_html(url: str) -> dict:
    """
    Fetch the article HTML and extract a best-effort summary/author.
    This is used for feeds (like CNN) that don't include a <description>.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; NewspaperBackend/1.0)"}
    try:
        with httpx.Client(
            timeout=20, follow_redirects=True, trust_env=False, headers=headers
        ) as client:
            r = client.get(url)
            r.raise_for_status()
            html = r.text
    except httpx.HTTPError:
        return {"summary": "", "content": "", "author": "", "image_url": ""}

    parser = _MetaExtractor()
    try:
        parser.feed(html)
    except Exception:
        return {"summary": "", "content": "", "author": "", "image_url": ""}

    summary = parser.og_description or parser.description
    image_url = parser.og_image or parser.twitter_image
    return {
        "summary": summary,
        "content": summary,
        "author": parser.author,
        "image_url": image_url,
    }


def _extract_image_from_xml(item) -> str:
    """
    Extract an image URL from common RSS/Atom patterns:
    - media:content / media:thumbnail (usually attributes url=...)
    - enclosure (type=image/*)
    - any descendant with url=... and (medium=image or type=image/*)
    """
    # 1) enclosure
    for el in item.iter():
        if _localname(el.tag) != "enclosure":
            continue
        url = _strip(el.get("url"))
        if not url:
            continue
        typ = _strip(el.get("type")).lower()
        if typ.startswith("image/") or not typ:
            return url

    # 2) media:* descendants
    for el in item.iter():
        ln = _localname(el.tag)
        if ln not in {"content", "thumbnail"}:
            continue
        url = _strip(el.get("url")) or _strip(el.get("href"))
        if not url:
            continue
        medium = _strip(el.get("medium")).lower()
        typ = _strip(el.get("type")).lower()
        if medium == "image" or typ.startswith("image/") or url.lower().endswith(
            (".jpg", ".jpeg", ".png", ".webp")
        ):
            return url

    return ""


def _parse_generic(item) -> dict:
    title = _text(_find_first_child(item, "title"))
    link = _extract_link(item)

    # Decide RSS vs Atom-ish based on children present
    if _find_first_child(item, "entry", "content", "summary", "published") and not _find_first_child(item, "description"):
        summary, content = _extract_summary_content_atom(item)
    else:
        summary, content = _extract_summary_content_rss(item)

    return {
        "title": title,
        "link": link,
        "summary": summary,
        "content": content,
        "author": _extract_author_generic(item),
        "image_url": _extract_image_from_xml(item),
        "language": "en",
    }


def sync_single_feed(feed: RSSFeed) -> None:
    """
    Fetch a single RSS feed and upsert its articles.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; NewspaperBackend/1.0)"}
    try:
        with httpx.Client(
            timeout=20, follow_redirects=True, trust_env=False, headers=headers
        ) as client:
            response = client.get(feed.url)
            response.raise_for_status()
    except httpx.HTTPError:
        return

    # Extremely lightweight XML parsing without external dependencies.
    # Each <item> (RSS) or <entry> (Atom) becomes an Article.
    from xml.etree import ElementTree as ET

    root = ET.fromstring(response.text)

    # RSS 2.0: <rss><channel><item>...</item></channel></rss>
    items = root.findall(".//item")
    if not items:
        # Atom or other formats: try <entry>
        items = root.findall(".//{*}entry")

    netloc = urlparse(feed.url).netloc.lower()
    is_atom = not root.findall(".//item") and bool(root.findall(".//{*}entry"))

    if "feeds.bbci.co.uk" in netloc or "bbc.co.uk" in netloc or "bbc.com" in netloc:
        parser = _parse_bbc_sport
    elif "cnn.com" in netloc:
        parser = _parse_cnn
    elif "openai.com" in netloc:
        parser = _parse_openai_atom if is_atom else _parse_openai_rss
    elif "simplecast.com" in netloc:
        parser = _parse_simplecast
    else:
        parser = _parse_generic

    for item in items:
        parsed = parser(item)
        title = _strip(parsed.get("title"))
        link = _strip(parsed.get("link"))

        if not title or not link:
            continue

        external_id = _extract_guid(item, fallback=link)

        summary = _strip(parsed.get("summary"))
        content = _strip(parsed.get("content")) or summary
        author = _strip(parsed.get("author")) or ""
        image_url = _strip(parsed.get("image_url")) or ""
        language = _strip(parsed.get("language")) or "en"

        # If the feed doesn't provide fields, enrich from HTML (CNN/OpenAI often need this).
        if (not summary or not content or not author or not image_url) and (
            "cnn.com" in netloc or "openai.com" in netloc
        ):
            enriched = _enrich_from_html(link)
            summary = summary or enriched.get("summary", "")
            content = content or enriched.get("content", "")
            if not author:
                author = enriched.get("author", "") or ""
            if not image_url:
                image_url = enriched.get("image_url", "") or ""

        # Published date
        published_dt: Optional[datetime] = None
        pub_el = _find_first_child(item, "pubDate", "published", "updated")
        if pub_el is not None and getattr(pub_el, "text", None):
            text = pub_el.text.strip()
            try:
                published_dt = parsedate_to_datetime(text)
            except (TypeError, ValueError):
                try:
                    published_dt = datetime.fromisoformat(text)
                except ValueError:
                    published_dt = None

        published_at = _guess_published_at(published_dt)

        # Upsert, but do not overwrite existing non-empty fields with empty strings.
        obj, created = Article.objects.get_or_create(
            feed=feed,
            external_id=external_id,
            defaults={
                "title": title[:512],
                "summary": summary,
                "content": content,
                "url": link,
                "image_url": image_url,
                "author": author,
                "language": language,
                "published_at": published_at,
            },
        )
        if not created:
            changed = False

            if title and obj.title != title:
                obj.title = title[:512]
                changed = True
            if link and obj.url != link:
                obj.url = link
                changed = True
            if summary and not obj.summary:
                obj.summary = summary
                changed = True
            if content and not obj.content:
                obj.content = content
                changed = True
            if author and not obj.author:
                obj.author = author
                changed = True
            if image_url and not obj.image_url:
                obj.image_url = image_url
                changed = True
            if language and not obj.language:
                obj.language = language
                changed = True
            if published_at and obj.published_at != published_at:
                obj.published_at = published_at
                changed = True

            if changed:
                obj.save()

    feed.last_fetched_at = timezone.now()
    feed.save(update_fields=["last_fetched_at"])

