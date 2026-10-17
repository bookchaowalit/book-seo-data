"""Public-page search must skip Google/YouTube *hosts*, not URLs mentioning them."""

from __future__ import annotations

import unittest
from unittest import mock

from book_seo import ingest

HTML = """
<a href="/url?q=https://blog.example/how-to-rank-on-google.com-in-2026&amp;sa=U">How to rank on Google</a>
<a href="/url?q=https://www.youtube.com/watch%3Fv%3Dx&amp;sa=U">A video result</a>
<a href="https://maps.google.com/place">Google Maps</a>
<a href="/url?q=https://www.bookchaowalit.com/&amp;sa=U">Book Chaowalit</a>
"""


class _Resp:
    status_code = 200
    text = HTML
    content = HTML.encode("utf-8")


@unittest.skipIf(ingest.BeautifulSoup is None, "beautifulsoup4 not installed")
class SearchHostFilterTests(unittest.TestCase):
    def test_only_google_and_youtube_hosts_are_skipped(self):
        allowed = mock.Mock(allowed=True)
        with (
            mock.patch.object(ingest, "evaluate_provider", return_value=allowed),
            mock.patch.object(ingest.httpx, "get", return_value=_Resp()),
            mock.patch("builtins.print"),
        ):
            _raw, _ctype, results = ingest.fetch_public_page_search_raw("rank")
        urls = [r["url"] for r in results]
        self.assertIn("https://blog.example/how-to-rank-on-google.com-in-2026", urls)
        self.assertIn("https://www.bookchaowalit.com/", urls)
        self.assertFalse(
            any("youtube.com/watch" in u or "maps.google.com" in u for u in urls)
        )


if __name__ == "__main__":
    unittest.main()
