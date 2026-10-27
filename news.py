"""Validated local and live news records for the RestEdge news workspace."""

import json
import ssl
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

import certifi


GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
MAX_FEED_BYTES = 2_000_000
REQUIRED_FIELDS = {"player_id", "title", "source", "url", "published_at", "item_type"}
INJURY_TERMS = (
    "injury", "injured", "questionable", "doubtful", "ruled out", "out for",
    "game-time decision", "gtd", "diagnosis", "surgery", "sprain", "strain",
    "fracture", "concussion", "illness", "recovery", "rehab", "return timetable",
)
AVAILABILITY_TERMS = (
    "available", "availability", "active", "inactive", "status", "returns",
    "returning", "cleared", "will play", "won't play", "will not play", "dnp",
)
REST_TERMS = (
    "rest", "rested", "load management", "minutes restriction", "minutes limit",
    "workload", "back-to-back", "maintenance",
)


@dataclass(frozen=True)
class NewsItem:
    player_id: int
    title: str
    source: str
    url: str
    published_at: datetime
    item_type: str


@dataclass(frozen=True)
class NewsFeedResult:
    items: tuple[NewsItem, ...]
    fetched_at: datetime
    provider: str
    error: str | None = None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _validated_url(value: str) -> str:
    parsed_url = urlparse(value)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("News item URL must use http or https.")
    return value


def load_player_news(file_path: str | Path, player_id: int) -> list[NewsItem]:
    """Load validated local news records for one player."""
    path = Path(file_path)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("News feed must be a JSON list.")

    items = []
    for record in payload:
        missing = REQUIRED_FIELDS.difference(record)
        if missing:
            raise ValueError(f"News item is missing fields: {', '.join(sorted(missing))}")
        if int(record["player_id"]) != int(player_id):
            continue
        items.append(
            NewsItem(
                player_id=int(record["player_id"]),
                title=str(record["title"]),
                source=str(record["source"]),
                url=_validated_url(str(record["url"])),
                published_at=_as_utc(
                    datetime.fromisoformat(str(record["published_at"]).replace("Z", "+00:00"))
                ),
                item_type=str(record["item_type"]),
            )
        )
    return sorted(items, key=lambda item: item.published_at, reverse=True)


def build_player_news_url(player_name: str, days: int = 7) -> str:
    """Build an exact-name Google News query focused on availability and workload."""
    safe_days = max(1, min(int(days), 30))
    query = quote_plus(
        f'"{player_name.strip()}" NBA '
        '(injury OR injured OR questionable OR doubtful OR status OR available OR rest '
        'OR "minutes restriction" OR workload OR recovery) '
        f'when:{safe_days}d'
    )
    return f"{GOOGLE_NEWS_RSS}?q={query}&hl=en-US&gl=US&ceid=US:en"


def _classify_item(title: str, source: str) -> str:
    title_lower = title.lower()
    source_lower = source.lower()
    relevant_terms = INJURY_TERMS + AVAILABILITY_TERMS + REST_TERMS
    if (
        source_lower == "nba.com" or "official" in source_lower
    ) and any(term in title_lower for term in relevant_terms):
        return "official_update"
    if any(term in title_lower for term in INJURY_TERMS):
        return "injury_update"
    if any(term in title_lower for term in REST_TERMS):
        return "rest_workload"
    if any(term in title_lower for term in AVAILABILITY_TERMS):
        return "availability_update"
    return "reporting"


def is_rest_or_injury_news(item: NewsItem) -> bool:
    """Return whether a headline is relevant to rest, injury, or availability."""
    title = item.title.lower()
    return item.item_type in {
        "official_update", "injury_update", "availability_update", "rest_workload"
    } or any(term in title for term in INJURY_TERMS + AVAILABILITY_TERMS + REST_TERMS)


def _news_priority(item: NewsItem) -> int:
    return {
        "official_update": 4,
        "injury_update": 3,
        "availability_update": 2,
        "rest_workload": 1,
    }.get(item.item_type, 0)


def parse_google_news_rss(
    payload: bytes,
    player_id: int,
    *,
    now: datetime | None = None,
    max_age_days: int = 7,
    limit: int = 12,
) -> list[NewsItem]:
    """Parse fresh, attributed headlines from a Google News RSS response."""
    if len(payload) > MAX_FEED_BYTES:
        raise ValueError("News response exceeded the maximum supported size.")
    root = ET.fromstring(payload)
    current_time = _as_utc(now or datetime.now(timezone.utc))
    cutoff = current_time - timedelta(days=max_age_days)
    items = []

    for element in root.findall("./channel/item"):
        title = (element.findtext("title") or "").strip()
        url = (element.findtext("link") or "").strip()
        published_text = (element.findtext("pubDate") or "").strip()
        source_element = element.find("source")
        source = (source_element.text or "Unknown source").strip() if source_element is not None else "Unknown source"
        if not title or not url or not published_text:
            continue
        published_at = _as_utc(parsedate_to_datetime(published_text))
        if published_at < cutoff or published_at > current_time + timedelta(hours=6):
            continue
        item = NewsItem(
            player_id=int(player_id),
            title=title,
            source=source,
            url=_validated_url(url),
            published_at=published_at,
            item_type=_classify_item(title, source),
        )
        if is_rest_or_injury_news(item):
            items.append(item)

    return merge_news_items(items)[: max(1, int(limit))]


def fetch_live_player_news(
    player_id: int,
    player_name: str,
    *,
    days: int = 7,
    limit: int = 12,
    timeout: int = 12,
) -> NewsFeedResult:
    """Fetch recent player headlines while returning a safe offline result on failure."""
    fetched_at = datetime.now(timezone.utc)
    request = Request(
        build_player_news_url(player_name, days),
        headers={"User-Agent": "Mozilla/5.0 RestEdge/1.0 (+sports research dashboard)"},
    )
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    try:
        with urlopen(request, timeout=timeout, context=ssl_context) as response:
            payload = response.read(MAX_FEED_BYTES + 1)
        items = parse_google_news_rss(
            payload,
            player_id,
            now=fetched_at,
            max_age_days=days,
            limit=limit,
        )
        return NewsFeedResult(tuple(items), fetched_at, "Google News RSS")
    except (HTTPError, URLError, TimeoutError, ET.ParseError, ValueError) as error:
        return NewsFeedResult((), fetched_at, "Google News RSS", str(error))


def merge_news_items(*collections: list[NewsItem] | tuple[NewsItem, ...]) -> list[NewsItem]:
    """Combine feeds, keep relevant items, and rank priority before freshness."""
    unique_items = {}
    for collection in collections:
        for item in collection:
            if not is_rest_or_injury_news(item):
                continue
            key = " ".join(item.title.lower().split())
            current = unique_items.get(key)
            if current is None or item.published_at > current.published_at:
                unique_items[key] = item
    return sorted(
        unique_items.values(),
        key=lambda item: (_news_priority(item), item.published_at),
        reverse=True,
    )

