import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from news import (
    NewsFeedResult,
    build_player_news_url,
    fetch_live_player_news,
    load_player_news,
    parse_google_news_rss,
)


class NewsTests(unittest.TestCase):
    def test_missing_feed_returns_no_items(self):
        self.assertEqual(load_player_news("missing-news.json", 1), [])

    def test_feed_filters_player_and_sorts_newest_first(self):
        records = [
            {"player_id": 1, "title": "Older", "source": "Source", "url": "https://example.com/1", "published_at": "2026-10-25T12:00:00+00:00", "item_type": "reporting"},
            {"player_id": 2, "title": "Different player", "source": "Source", "url": "https://example.com/2", "published_at": "2026-10-26T12:00:00+00:00", "item_type": "reporting"},
            {"player_id": 1, "title": "Newer", "source": "Official", "url": "https://example.com/3", "published_at": "2026-10-26T11:00:00+00:00", "item_type": "official_status"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "news.json"
            path.write_text(json.dumps(records), encoding="utf-8")
            items = load_player_news(path, 1)
        self.assertEqual([item.title for item in items], ["Newer", "Older"])

    def test_live_url_uses_exact_player_name_and_freshness_window(self):
        url = build_player_news_url("Jalen Suggs", days=7)
        self.assertIn("%22Jalen+Suggs%22+NBA+when%3A7d", url)

    def test_rss_parser_keeps_fresh_items_and_classifies_injury_news(self):
        payload = b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss><channel>
          <item><title>Jalen Suggs Injury Update</title><link>https://news.example.com/1</link><pubDate>Mon, 26 Oct 2026 18:45:00 GMT</pubDate><source>NBA.com</source></item>
          <item><title>Old story</title><link>https://news.example.com/2</link><pubDate>Thu, 01 Oct 2026 18:45:00 GMT</pubDate><source>Example</source></item>
        </channel></rss>"""
        items = parse_google_news_rss(
            payload,
            4,
            now=datetime(2026, 10, 26, 20, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].item_type, "official_update")

    def test_live_fetch_returns_safe_result_on_provider_failure(self):
        with patch("news.urlopen", side_effect=TimeoutError("timed out")):
            result = fetch_live_player_news(4, "Jalen Suggs")
        self.assertIsInstance(result, NewsFeedResult)
        self.assertEqual(result.items, ())
        self.assertIn("timed out", result.error)


if __name__ == "__main__":
    unittest.main()

