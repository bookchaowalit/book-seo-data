"""Runtime configuration for book-seo-data."""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", str(PROJECT_ROOT / "data")))
FIXTURES_DIR = Path(os.environ.get("FIXTURES_DIR", str(PROJECT_ROOT / "fixtures")))

REPO_NAME = "book-seo-data"
DOMAIN = "seo"
SCHEMA_VERSION = "seo.v1"
RECORDS_FILE = "seo_rankings.csv"
HISTORY_FILE = "seo_rankings_history.csv"
LINEAGE_FILE = "lake_lineage.json"
# keyword + target_domain + location + device
ID_FIELDS = ["keyword", "target_domain", "location", "device"]
ID_SEP = ":"

LAKE_SOURCE = REPO_NAME
LAKE_DOMAIN = "seo"
LAKE_DATASET_RANKINGS = "seo_rankings"
LAKE_DATASET_HISTORY = "seo_rankings_history"
LAKE_BRONZE_SCHEMA_VERSION = "1"
LAKE_PRIVACY_CLASS = "public"
LAKE_RETENTION_CLASS = "operational"

DEFAULT_LOCATION = os.environ.get("SEO_LOCATION", "global")
DEFAULT_DEVICE = os.environ.get("SEO_DEVICE", "desktop")


def env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


FREE_ONLY = env_bool("FREE_ONLY", True)
ALLOW_PAID_PROVIDERS = env_bool("ALLOW_PAID_PROVIDERS", False)
ALLOW_EXTERNAL_WRITES = env_bool("ALLOW_EXTERNAL_WRITES", False)
ALLOW_REFRESH = env_bool("ALLOW_REFRESH", False)
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN", "")
API_HOST = os.environ.get("API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("API_PORT", "8106"))
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "15"))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "2"))
MAX_RESPONSE_BYTES = int(os.environ.get("MAX_RESPONSE_BYTES", str(2_000_000)))
STALE_AFTER_HOURS = float(os.environ.get("STALE_AFTER_HOURS", "24"))
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "20"))

DATA_LAKE_URI = os.environ.get(
    "SOLO_EMPIRE_DATA_LAKE_URI",
    os.environ.get("DATA_LAKE_URI", ""),
)
SOLO_EMPIRE_ROOT = os.environ.get("SOLO_EMPIRE_ROOT", "")
LAKE_READ_MODE = os.environ.get("LAKE_READ_MODE", "parquet").strip().lower()
LAKE_READ_FALLBACK = os.environ.get("LAKE_READ_FALLBACK", "error").strip().lower()
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
