"""Lake-first tests for book-seo-data."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from book_seo import config, lake
from book_seo.ingest import run_live_ingest
from book_seo.store import seed_lake_from_captures


SAMPLE_RANKING = {
    "keyword": "python developer thailand",
    "total_results": 10,
    "found": True,
    "best_rank": 5,
    "best_url": "https://bookchaowalit.com/python",
    "best_domain": "bookchaowalit.com",
    "best_title": "Python Developer",
    "all_positions": [
        {
            "rank": 5,
            "url": "https://bookchaowalit.com/python",
            "domain": "bookchaowalit.com",
            "title": "Python Developer",
        }
    ],
}



def _shared_adapter_available() -> bool:
    return lake.shared_runtime_available()


class IdentityTests(unittest.TestCase):
    def test_stable_id_keyword_domain_location_device(self):
        rid = lake.stable_ranking_id(
            keyword="Python Developer Thailand",
            target_domain="Bookchaowalit.com",
            location="TH",
            device="mobile",
        )
        again = lake.stable_ranking_id(
            keyword="python developer thailand",
            target_domain="bookchaowalit.com",
            location="th",
            device="mobile",
        )
        self.assertEqual(rid, again)
        self.assertIn("python-developer-thailand", rid)
        self.assertIn("bookchaowalit.com", rid)
        self.assertIn("th", rid)
        self.assertIn("mobile", rid)

    def test_normalize_fields(self):
        rec = lake.normalize_ranking_record(
            {
                "keyword": "python developer thailand",
                "rank": 5,
                "result_url": "https://bookchaowalit.com",
                "result_title": "Python Developer",
                "found": True,
            },
            provider="public_page_check",
            target_domain="bookchaowalit.com",
            location="global",
            device="desktop",
            observed_at="2026-08-07T12:00:00Z",
        )
        self.assertEqual(rec["rank"], 5)
        self.assertEqual(rec["result_url"], "https://bookchaowalit.com")
        self.assertEqual(rec["result_title"], "Python Developer")
        self.assertEqual(rec["observed_at"], "2026-08-07T12:00:00Z")
        self.assertEqual(rec["event_time"], "2026-08-07T12:00:00Z")
        self.assertEqual(rec["id"], rec["id"])  # stable


class OrderingTests(unittest.TestCase):
    @unittest.skipUnless(
        _shared_adapter_available(),
        "shared data_lake runtime not installed (pip install -e .[lake])",
    )
    def test_fail_closed_no_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)

            def boom(**_k):
                raise lake.LakeIngestError("simulated")

            with mock.patch(
                "book_seo.ingest.fetch_public_page_search_raw",
                return_value=(
                    b"<html>results</html>",
                    "text/html",
                    [{"url": "https://bookchaowalit.com", "title": "X"}],
                ),
            ):
                with mock.patch.object(
                    lake, "ingest_provider_payload", side_effect=boom
                ):
                    with self.assertRaises(lake.LakeIngestError):
                        run_live_ingest(
                            keywords=["python developer"],
                            target_domains=["bookchaowalit.com"],
                            output_dir=out,
                            data_lake_uri=str(out / "lake"),
                            write_history=False,
                            project_csv=True,
                        )
            self.assertFalse((out / "seo_rankings.csv").exists())


@unittest.skipUnless(
    lake.shared_runtime_available(),
    "shared data_lake runtime not installed (pip install -e .[lake])",
)
class RealLakeTests(unittest.TestCase):
    def test_html_landing_and_replay(self):
        try:
            import pyarrow  # noqa: F401
        except ImportError:
            self.skipTest("pyarrow missing")

        with tempfile.TemporaryDirectory() as tmp:
            lake_uri = str(Path(tmp) / "lake")
            html = b"<html><body>python developer results</body></html>"
            results = seed_lake_from_captures(
                [
                    {
                        "provider": "public_page_check",
                        "raw": html,
                        "ranking": SAMPLE_RANKING,
                        "target_domains": ["bookchaowalit.com", "chaowalit.com"],
                        "content_type": "text/html",
                        "input_format": "html",
                    }
                ],
                data_lake_uri=lake_uri,
            )
            landings = [r for r in results if r["raw_key"].endswith(".html")]
            self.assertTrue(landings)
            raw_key = landings[0]["raw_key"]
            self.assertIn("provider=public_page_check", raw_key)
            self.assertEqual(
                lake.landing_object_bytes(raw_key, data_lake_uri=lake_uri), html
            )
            # Replay identity
            self.assertEqual(
                lake.landing_object_bytes(raw_key, data_lake_uri=lake_uri),
                lake.landing_object_bytes(raw_key, data_lake_uri=lake_uri),
            )
            rows = lake.read_bronze_rows(
                config.LAKE_DATASET_RANKINGS, data_lake_uri=lake_uri
            )
            # One row per target domain
            self.assertEqual(len(rows), 2)
            payloads = [lake.parse_payload_json(r) for r in rows]
            domains = {p["target_domain"] for p in payloads}
            self.assertEqual(domains, {"bookchaowalit.com", "chaowalit.com"})
            found = next(
                p for p in payloads if p["target_domain"] == "bookchaowalit.com"
            )
            self.assertEqual(int(found["rank"]), 5)
            self.assertEqual(found["result_url"], "https://bookchaowalit.com/python")

    def test_stable_id_replay(self):
        a = lake.ranking_records_from_check(
            SAMPLE_RANKING,
            provider="public_page_check",
            target_domains=["bookchaowalit.com"],
        )
        b = lake.ranking_records_from_check(
            SAMPLE_RANKING,
            provider="public_page_check",
            target_domains=["bookchaowalit.com"],
        )
        self.assertEqual([r["id"] for r in a], [r["id"] for r in b])


class SharedAdapterTests(unittest.TestCase):
    def test_contract(self):
        self.assertEqual(config.LAKE_SOURCE, "book-seo-data")
        self.assertEqual(config.LAKE_DOMAIN, "seo")
        self.assertEqual(config.LAKE_DATASET_RANKINGS, "seo_rankings")
        self.assertEqual(config.SCHEMA_VERSION, "seo.v1")
        self.assertEqual(int(config.API_PORT), 8106)


if __name__ == "__main__":
    src = Path(__file__).resolve().parents[1] / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    unittest.main()
