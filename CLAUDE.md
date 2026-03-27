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
- `adguard_exporter/parsers/querylog.py`: querylog parsing and client extraction
- `adguard_exporter/parsers/reason.py`: explicit `reason` classification
- `adguard_exporter/collectors/querylog.py`: incremental querylog processing
- `adguard_exporter/services/client_mapping.py`: friendly client mapping
- `adguard_exporter/state/store.py`: state model and interface
- `adguard_exporter/state/file.py`: file-backed persisted state
- `adguard_exporter/metrics/exporter.py`: metric building and exposition
- `app.py`: root runtime entrypoint
- `tests/`: parser, state, and endpoint test coverage

## What The Exporter Does Today
- authenticates against the AdGuard API
- reads `/control/stats`
- reads `/control/querylog`
- reads `/control/clients`
- persists local querylog-derived state
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
1. AdGuard querylog schema is not fully stable across versions.
2. Querylog is still a snapshot source at the API level.
3. Querylog-derived cumulative metrics now depend on persisted local exporter state.
4. Resetting exporter state resets locally processed querylog counters.
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

### State explicitly
If the exporter derives cumulative values from a snapshot source, the local persisted state is part of the design, not an implementation detail.

## Metric Guidance
- Default to low-cardinality labels.
- New labels need clear dashboard value.
- Avoid unbounded dimensions.
- Be careful with `_total` suffixes when the value is not a real monotonic source counter.
- Querylog-derived metrics should be documented as exporter-processed cumulative values.

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

## Querylog Processing Guidance
Blocked-state detection should stay explicit and deterministic.

Preferred rules:
- use `reason` classification first when possible
- return `True`, `False`, or `None`
- do not invent certainty when data is unclear
- preserve uncertainty through debug metrics

Querylog collection rules:
- treat `/control/querylog` as a rolling snapshot
- process only new entries using persisted state
- use bounded deduplication fingerprints
- keep the design simple enough for homelab operations

## Friendly Device Mapping
Mapping IPs to friendly device names is desirable, but it must stay simple and bounded.

Preferred approach:
- static mapping first via AdGuard client data
- deterministic fallback to raw client identity
- no dynamic discovery system unless it clearly pays for itself

## State and Persistence Guidance
The exporter now persists local querylog processing state.

Implications:
- the state file is operationally important
- if state is lost, locally processed querylog counters reset
- state should be persisted across container restarts if continuity matters
- the state mechanism should remain file-based and simple unless a stronger need appears

## Error Handling Guidance
The exporter should fail visibly and degrade gracefully.

Preferred behavior:
- if stats fail, expose exporter failure clearly
- if querylog fails, keep global stats available when possible
- if client mapping fails, continue with raw client identity
- log enough context to troubleshoot
- avoid excessive repeated log noise

Useful future internal metrics:
- last successful scrape timestamp
- scrape duration
- API request failure counters
- state load/save failure counters

## Testing Guidance
Tests should target the unstable and high-value parts first.

Current highest-value areas:
1. client extraction
2. blocked-state extraction
3. querylog summary behavior
4. incremental deduplication
5. state persistence behavior
6. metrics endpoint behavior using fake clients and fake state stores

Keep the test suite focused. Prefer deterministic fixtures over a heavy integration harness.

## Near-Term Priorities
- improve logging and internal observability
- add more tests before semantic metric changes
- revisit metric naming and docs for querylog-derived counters
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
