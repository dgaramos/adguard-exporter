# CLAUDE.md

## Project Intent
`adguard_exporter` is a custom Python Prometheus exporter for AdGuard Home used in a homelab environment.

The project exists because AdGuard Home does not expose the right metrics for the observability goals of this setup. The exporter should remain small, robust, and operationally cheap while still giving enough visibility for useful Grafana dashboards.

## Main Objective
Collect data from the AdGuard Home API and expose Prometheus metrics that are practical for monitoring DNS traffic, blocking behavior, and client-level trends.

## Environment
- Raspberry Pi 5
- Linux
- Docker
- AdGuard Home running in a container
- Prometheus scraping `/metrics`
- Grafana for dashboards
- Loki + Alloy for logs

## High-Level Architecture

```text
Devices -> AdGuard Home (DNS)
Devices -> AdGuard API -> adguard_exporter -> Prometheus -> Grafana
                                         -> Loki / Alloy
```

## Current Code Structure
- `adguard_exporter/app.py`: Flask app and route wiring
- `adguard_exporter/config.py`: environment configuration
- `adguard_exporter/clients/adguard.py`: AdGuard API client
- `adguard_exporter/parsers/querylog.py`: parsing heuristics and querylog summarization
- `adguard_exporter/metrics/exporter.py`: metric building and exposition
- `app.py`: root runtime entrypoint
- `tests/`: parser and endpoint test coverage

## What The Exporter Does Today
- authenticates against the AdGuard API
- reads `/control/stats`
- reads `/control/querylog`
- exposes metrics at `/metrics`

## Existing Metrics
### Global
- `adguard_num_dns_queries`
- `adguard_num_blocked_filtering`
- `adguard_avg_processing_time_seconds`
- `adguard_blocked_ratio`

### Hourly series
- `adguard_dns_queries_hour{hour}`
- `adguard_blocked_filtering_hour{hour}`

### Top lists
- `adguard_top_queried_domain_queries{name}`
- `adguard_top_client_queries{name}`
- `adguard_top_blocked_domain_queries{name}`
- `adguard_top_upstream_responses{upstream}`
- `adguard_top_upstream_avg_time_seconds{upstream}`

### Per-client
- `adguard_client_queries_total{client}`
- `adguard_client_blocked_total{client}`
- `adguard_client_blocked_ratio{client}`

### Debug / health
- `adguard_exporter_up`
- `adguard_querylog_up`
- `adguard_querylog_entries_total`
- `adguard_querylog_blocked_detected_total`
- `adguard_querylog_nonblocked_detected_total`
- `adguard_querylog_unknown_blocked_state_total`

## Operational Reality
This is a homelab service, but engineering quality still matters.

The exporter should be:
- predictable
- observable
- easy to debug
- safe for Prometheus
- cheap to run

## Key Constraints
- Avoid overengineering.
- Prefer explicit, readable code.
- Preserve existing metric compatibility when possible.
- Do not break dashboards casually.
- Keep Prometheus cardinality bounded.
- Prefer Prometheus for aggregates and Loki for detail.
- Add tests where they meaningfully reduce regression risk.

## Known Limitations
1. Blocked vs non-blocked classification is still heuristic.
2. AdGuard querylog schema is not fully stable across versions.
3. `unknown_blocked_state` can reduce trust in per-client blocked ratios.
4. Querylog is a snapshot, not a complete historical stream.
5. Per-client per-domain metrics are not implemented.
6. `client + domain` metrics are a cardinality risk and must be treated carefully.

## Design Principles
### Simplicity first
Use the smallest design that solves the current problem.

### Compatibility first
Preserve existing dashboards and metric contracts unless the improvement clearly justifies change.

### Cardinality awareness
Label growth is a design constraint, not a cleanup item for later.

### Parse defensively
Assume AdGuard response fields may be absent, renamed, or inconsistent.

### Right data in the right system
Prometheus is for bounded aggregates and alerting. Loki is for detail, event inspection, and high-cardinality exploration.

## Metric Guidance
- Default to low-cardinality labels.
- New labels need clear dashboard value.
- Avoid unbounded dimensions.
- Treat snapshot-derived metrics carefully.
- Be careful with `_total` suffixes when the value is not a real monotonic counter.

### Safe-ish label categories
- fixed upstreams
- bounded top-N outputs
- explicit mapped device names
- small status-like dimensions

### Dangerous label categories
- raw domains across general traffic
- raw client IPs without normalization
- `client + domain` combinations
- labels that grow with user behavior over time

## Querylog Parsing Guidance
Blocked-state detection should stay heuristic but explicit.

Preferred rules:
- use deterministic evaluation order
- check multiple known fields defensively
- return `True`, `False`, or `None`
- do not invent certainty when data is unclear
- preserve uncertainty through debug metrics

Good parser qualities:
- easy to test
- easy to extend when AdGuard changes fields
- tolerant of schema variation

## Friendly Device Mapping
Mapping IPs to friendly device names is desirable, but it must stay simple and bounded.

Preferred approach:
- static mapping first
- deterministic fallback to raw client identity
- no dynamic discovery system unless it clearly pays for itself

Acceptable forms:
- environment variable
- small YAML or JSON mapping file

## Error Handling Guidance
The exporter should fail visibly and degrade gracefully.

Preferred behavior:
- if stats fail, expose exporter failure clearly
- if querylog fails, keep global stats available when possible
- log enough context to troubleshoot
- avoid excessive repeated log noise

Useful future internal metrics:
- last successful scrape timestamp
- scrape duration
- API request failure counters
- bounded parse failure counters if useful

## Testing Guidance
Tests should target the unstable and high-value parts first.

Current highest-value areas:
1. client extraction
2. blocked-state extraction
3. querylog summary behavior
4. metrics endpoint behavior using fake clients

Keep the test suite focused. Prefer deterministic fixtures over a heavy integration harness.

## Near-Term Priorities
- improve querylog parsing robustness
- improve logging and internal observability
- add more tests before semantic metric changes
- revisit snapshot metric naming when there is a safe migration path
- design a bounded approach for friendly device naming
- design any per-client top-domain feature with explicit cardinality controls

## Collaboration Style
Work should be:
- direct
- technical
- pragmatic
- explicit about trade-offs
- conscious of Prometheus and Grafana impact
- ready to implement, not just discuss
