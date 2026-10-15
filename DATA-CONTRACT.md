# SEO dataset contract (`seo.v1`)

Owner: `bookchaowalit/marketing-seo-ranking-data` (product id `book-seo-data`).
The compatible datasets remain `seo_rankings` and `seo_rankings_history`.
Their historical names cover owned-page reachability/provenance; names alone
are never evidence of a SERP position.

## Approved scheduled capture

`scripts/run_seo.py` invokes `scripts/scrape_seo_rankings.py` to check public
homepages configured for the owner's domains. The default domains are
`bookchaowalit.com` and `chaowalit.com`. This command checks HTTP response,
page title and canonical URL, and writes the exact response bytes plus capture
CSV projections. It does not query a search engine or collect search rank.

The snapshot fields are `captured_at`, `domain`, `url`, `http_status`, `title`,
`canonical`, `content_length`, `data_status`, `rank`, `keyword`, and `source`.
Scheduled `rank` and `keyword` fields are blank and `source` is
`public_page_check`. The history retains observation time, domain, URL, HTTP
status, title, page status and source; neither file is a consumer API.

The capture replay adapter in `data-lake-pipelines` maps these rows into the
existing lake/API item shape:

| Field | Meaning for an owned-page observation |
| --- | --- |
| `capture_kind` | `owned_page_provenance` |
| `provider` | `public_page_check` |
| `keyword` | Capture label; replay supplies `owned-page\|<url>` when blank |
| `target_domain` | Observed owned domain |
| `result_url`, `result_title` | Observed page URL/title, not a SERP listing |
| `found` | Page reachable with an accepted HTTP status and page status |
| `rank`, `best_rank`, `total_results` | Blank; unknown is never rank zero or position one |
| `page_http_status`, `page_data_status` | Capture response/status evidence |
| `page_canonical_url`, `page_content_length` | Canonical link and captured page size |
| `observed_at`, `event_time` | Capture observation time |
| `raw_object_key` | Exact-byte landing provenance |

The stable record identity remains `keyword:target_domain:location:device`;
history records add the existing observation suffix. Consumers must inspect
`capture_kind` and `provider` before interpreting ranking fields. Separate
fixture/search-result ingest paths can produce `serp_ranking` records; an
owned-page response does not establish that kind or a measured search rank.
Paid search providers remain blocked by the default provider policy.

## Storage and compatibility

Bronze paths remain `bronze/domain=seo/dataset=seo_rankings` and
`bronze/domain=seo/dataset=seo_rankings_history`, with Bronze schema `1`,
source `book-seo-data` and envelope `seo.v1`. Consumers read `GET /v1/records`
and `GET /v1/history` on port `8106` (or the approved lake reader), preserving
observation/provenance fields. The API never reads scheduler CSVs directly.

This documentation clarifies existing semantics; it does not rename datasets,
fields, ports or `schema_version`. A future rename or incompatible semantic
change requires a new schema version, an explicit migration, and a consumer
transition in accordance with the portfolio versioning policy. Do not silently
reinterpret existing `seo.v1` reachability records as ranking measurements.
