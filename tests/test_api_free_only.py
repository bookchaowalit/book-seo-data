"""Offline tests for book-seo-data free-only API + lake-first rankings."""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from book_seo import config, lake, policy
from book_seo.api import DataProductHandler
from book_seo.store import (
    load_csv_projection,
    load_history,
    load_records,
    seed_fixtures,
    seed_lake_from_captures,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"

SAMPLE_RANKING = {
    "keyword": "python developer thailand",
    "total_results": 20,
    "found": True,
    "best_rank": 5,
    "best_url": "https://bookchaowalit.com",
    "best_domain": "bookchaowalit.com",
    "best_title": "Python Developer",
    "all_positions": [
        {
            "rank": 5,
            "url": "https://bookchaowalit.com",
            "domain": "bookchaowalit.com",
            "title": "Python Developer",
        }
    ],
}


def _set_data_dir(path: Path):
    return mock.patch.object(config, "DATA_DIR", path)


def _set_lake_uri(uri: str):
    return mock.patch.object(config, "DATA_LAKE_URI", uri)


def _set_read_mode(mode: str, fallback: str = "error"):
    return mock.patch.multiple(
        config,
        LAKE_READ_MODE=mode,
        LAKE_READ_FALLBACK=fallback,
    )


def _lake_deps_available() -> bool:
    try:
        import duckdb  # noqa: F401
        import pyarrow  # noqa: F401
    except ImportError:
        return False
    return lake.shared_runtime_available()


@unittest.skipUnless(
    _lake_deps_available(),
    "pyarrow/duckdb + shared data_lake runtime required (pip install -e .[lake])",
)
class StoreLakeTests(unittest.TestCase):
    def test_bronze_not_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            lake_uri = str(Path(tmp) / "lake")
            seed_lake_from_captures(
                [
                    {
                        "provider": "public_page_check",
                        "raw": b"<html>results for python developer</html>",
                        "ranking": SAMPLE_RANKING,
                        "target_domains": ["bookchaowalit.com"],
                        "content_type": "text/html",
                        "input_format": "html",
                        "location": "global",
                        "device": "desktop",
                    }
                ],
                data_lake_uri=lake_uri,
            )
            with _set_lake_uri(lake_uri):
                payload = load_records()
            self.assertEqual(payload["source_kind"], "bronze_parquet")
            self.assertNotIn("seo_rankings.csv", payload["path"])
            self.assertGreaterEqual(len(payload["items"]), 1)
            item = payload["items"][0]
            self.assertEqual(item["keyword"], "python developer thailand")
            self.assertIn("rank", item)
            self.assertIn("result_url", item)
            self.assertIn("observed_at", item)
            self.assertTrue(item["raw_object_key"].startswith("landing/"))

    def test_csv_does_not_feed_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            lake_uri = str(root / "empty")
            Path(lake_uri).mkdir()
            with mock.patch.object(config, "FIXTURES_DIR", FIXTURE_ROOT):
                seed_fixtures(data_dir)
            self.assertGreaterEqual(
                len(load_csv_projection(kind="records", data_dir=data_dir)["items"]), 1
            )
            with _set_lake_uri(lake_uri), _set_data_dir(data_dir):
                self.assertEqual(load_records()["items"], [])

    def test_iceberg_and_parquet_reads_have_same_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            lake_uri = str(Path(tmp) / "lake")
            seed_lake_from_captures(
                [
                    {
                        "provider": "offline_fixtures",
                        "raw": b"<html>seo results</html>",
                        "ranking": SAMPLE_RANKING,
                        "target_domains": ["bookchaowalit.com"],
                        "content_type": "text/html",
                        "input_format": "html",
                    }
                ],
                data_lake_uri=lake_uri,
            )

            def read_catalog_rows(contract, dataset, *, data_lake_uri=None, sql=None):
                return lake.read_bronze_rows(
                    dataset, data_lake_uri=data_lake_uri, sql=sql
                )

            with _set_lake_uri(lake_uri), _set_read_mode("parquet"):
                expected_rankings = load_records()
                expected_history = load_history()
            with _set_lake_uri(lake_uri), _set_read_mode("iceberg"), mock.patch(
                "data_lake.product_store.read_iceberg_rows",
                side_effect=read_catalog_rows,
            ):
                actual_rankings = load_records()
                actual_history = load_history()

            self.assertEqual(actual_rankings["items"], expected_rankings["items"])
            self.assertEqual(actual_history["items"], expected_history["items"])
            self.assertEqual(actual_rankings["source_kind"], "iceberg_rest_duckdb")
            self.assertEqual(actual_history["source_kind"], "iceberg_rest_duckdb")
            self.assertEqual(actual_rankings["read_mode"], "iceberg")

    def test_iceberg_mode_fallback_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            lake_uri = str(Path(tmp) / "lake")
            seed_lake_from_captures(
                [
                    {
                        "provider": "offline_fixtures",
                        "raw": b"<html>seo results</html>",
                        "ranking": SAMPLE_RANKING,
                        "target_domains": ["bookchaowalit.com"],
                        "content_type": "text/html",
                        "input_format": "html",
                    }
                ],
                data_lake_uri=lake_uri,
            )
            with _set_lake_uri(lake_uri), _set_read_mode("iceberg", "parquet"), mock.patch(
                "data_lake.product_store.read_iceberg_rows",
                side_effect=lake.LakeUnavailable("catalog unavailable"),
            ):
                payload = load_records()

            self.assertGreaterEqual(len(payload["items"]), 1)
            self.assertEqual(payload["source_kind"], "bronze_parquet_fallback")
            self.assertIn("catalog unavailable", payload["fallback_reason"])

    def test_iceberg_mode_fails_closed_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            lake_uri = str(Path(tmp) / "lake")
            seed_lake_from_captures(
                [
                    {
                        "provider": "offline_fixtures",
                        "raw": b"<html>seo results</html>",
                        "ranking": SAMPLE_RANKING,
                        "target_domains": ["bookchaowalit.com"],
                        "content_type": "text/html",
                        "input_format": "html",
                    }
                ],
                data_lake_uri=lake_uri,
            )
            with _set_lake_uri(lake_uri), _set_read_mode("iceberg", "error"), mock.patch(
                "data_lake.product_store.read_iceberg_rows",
                side_effect=lake.LakeUnavailable("catalog credentials unavailable"),
            ):
                payload = load_records()

            self.assertEqual(payload["data_status"], "error")
            self.assertEqual(payload["items"], [])
            self.assertEqual(payload["source_kind"], "iceberg_rest_duckdb")
            self.assertIn("catalog credentials unavailable", payload["error"])


class PolicyTests(unittest.TestCase):
    def test_public_page_free(self):
        self.assertTrue(policy.evaluate_provider("public_page_check").allowed)
        self.assertTrue(policy.evaluate_provider("offline_fixtures").allowed)

    def test_paid_blocked_before_network(self):
        with mock.patch.object(config, "FREE_ONLY", True):
            self.assertFalse(policy.evaluate_provider("firecrawl").allowed)
            self.assertFalse(policy.evaluate_provider("google_cse").allowed)
            self.assertFalse(policy.evaluate_provider("paid_serp").allowed)


@unittest.skipUnless(
    _lake_deps_available(),
    "pyarrow/duckdb + shared data_lake runtime required (pip install -e .[lake])",
)
class ApiContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.data_dir = root / "data"
        self.data_dir.mkdir()
        self.lake_uri = str(root / "lake")
        seed_lake_from_captures(
            [
                {
                    "provider": "public_page_check",
                    "raw": b"<html>seo results</html>",
                    "ranking": SAMPLE_RANKING,
                    "target_domains": ["bookchaowalit.com"],
                    "content_type": "text/html",
                }
            ],
            data_lake_uri=self.lake_uri,
            data_dir=self.data_dir,
        )
        self.data_patch = _set_data_dir(self.data_dir)
        self.lake_patch = _set_lake_uri(self.lake_uri)
        self.read_patch = _set_read_mode("parquet", "error")
        self.data_patch.start()
        self.lake_patch.start()
        self.read_patch.start()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), DataProductHandler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.lake_patch.stop()
        self.data_patch.stop()
        self.read_patch.stop()
        self.tmp.cleanup()

    def _get(self, path: str):
        try:
            with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_metadata(self):
        status, body = self._get("/v1/metadata")
        self.assertEqual(status, 200)
        meta = body["items"][0]
        self.assertEqual(meta["storage_model"], "lake_first_bronze_duckdb")
        self.assertEqual(meta["lake_domain"], "seo")
        self.assertEqual(meta["capture_mode"], "per_provider_query")
        self.assertEqual(meta["records_source_kind"], "bronze_parquet")
        self.assertEqual(meta["read_mode"], "parquet")
        self.assertEqual(meta["read_fallback"], "error")

    def test_metadata_reports_iceberg_mode(self):
        def read_catalog_rows(contract, dataset, *, data_lake_uri=None, sql=None):
            return lake.read_bronze_rows(
                dataset, data_lake_uri=data_lake_uri, sql=sql
            )

        with _set_read_mode("iceberg"), mock.patch(
            "data_lake.product_store.read_iceberg_rows",
            side_effect=read_catalog_rows,
        ):
            status, body = self._get("/v1/metadata")

        self.assertEqual(status, 200)
        meta = body["items"][0]
        self.assertEqual(meta["storage_model"], "lake_first_iceberg_rest_duckdb")
        self.assertEqual(meta["records_source_kind"], "iceberg_rest_duckdb")
        self.assertEqual(meta["history_source_kind"], "iceberg_rest_duckdb")
        self.assertEqual(meta["read_mode"], "iceberg")

    def test_api_without_csv(self):
        self.assertFalse(any(self.data_dir.glob("*.csv")))
        status, body = self._get("/v1/records")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(body["items"]), 1)
        (self.data_dir / config.RECORDS_FILE).write_text(
            "scraped_at,keyword,found,best_rank,best_domain,best_url,best_title,total_results\n"
            "2099-01-01,FAKE,True,1,fake.com,https://fake,Fake,1\n",
            encoding="utf-8",
        )
        status, body = self._get("/v1/records")
        kws = {i["keyword"] for i in body["items"]}
        self.assertIn("python developer thailand", kws)
        self.assertNotIn("FAKE", kws)

    def test_refresh_forbidden(self):
        req = Request(
            f"http://127.0.0.1:{self.port}/v1/refresh", data=b"{}", method="POST"
        )
        try:
            urlopen(req, timeout=5)
            self.fail("expected 403")
        except HTTPError as e:
            self.assertEqual(e.code, 403)


class SmokeCompileTests(unittest.TestCase):
    def test_modules_import(self):
        from book_seo import api, config as cfg, store  # noqa: F401 (import smoke)

        self.assertEqual(cfg.SCHEMA_VERSION, "seo.v1")
        self.assertEqual(int(cfg.API_PORT), 8106)
        self.assertEqual(cfg.LAKE_DOMAIN, "seo")
        self.assertEqual(cfg.LAKE_DATASET_RANKINGS, "seo_rankings")
        self.assertEqual(cfg.LAKE_READ_MODE, "parquet")
        self.assertEqual(cfg.LAKE_READ_FALLBACK, "error")
        self.assertTrue(hasattr(store, "load_csv_projection"))


if __name__ == "__main__":
    unittest.main()
