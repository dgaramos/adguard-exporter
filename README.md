# adguard_exporter

A custom Python Prometheus exporter for AdGuard Home.

This project exists because AdGuard Home's native Prometheus metrics are not enough for the level of observability needed in this homelab setup. The exporter collects data from the AdGuard API, reshapes it into Prometheus metrics, and makes it easier to build Grafana dashboards around DNS usage, blocking behavior, and client-level visibility.

## Goals
- Expose useful AdGuard Home metrics in Prometheus format
- Provide client-focused visibility that is hard to get from AdGuard's built-in metrics
- Stay small, understandable, and easy to maintain
- Improve observability without creating an overly complex service

## Architecture
Current flow:

```text
Devices -> AdGuard Home (DNS)
Devices -> AdGuard API -> adguard_exporter -> Prometheus -> Grafana
                                         -> Loki / Alloy for logs
```

The exporter currently:
- authenticates against the AdGuard API
- reads `/control/stats`
- reads `/control/querylog`
- reads `/control/clients`
- persists local querylog processing state
- exposes Prometheus metrics at `/metrics`

## Project Structure

```text
.
├── adguard_exporter/
│   ├── clients/
│   │   └── adguard.py
│   ├── collectors/
│   │   └── querylog.py
│   ├── metrics/
│   │   └── exporter.py
│   ├── parsers/
│   │   ├── querylog.py
│   │   └── reason.py
│   ├── services/
│   │   └── client_mapping.py
│   ├── state/
│   │   ├── file.py
│   │   └── store.py
│   ├── __init__.py
│   ├── app.py
│   └── config.py
├── tests/
│   ├── test_app.py
│   ├── test_querylog_parser.py
│   └── test_state.py
├── AGENTS.md
├── CLAUDE.md
├── Dockerfile
├── README.md
├── app.py
├── docker-compose.yml
├── requirements-dev.txt
└── requirements.txt
```

## Metrics

### Global metrics
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

### Per-client metrics
Compatibility aliases:
- `adguard_client_queries_total{client}`
- `adguard_client_blocked_total{client}`
- `adguard_client_blocked_ratio{client}`

Explicit processed metrics:
- `adguard_client_queries_processed_total{client}`
- `adguard_client_blocked_processed_total{client}`
- `adguard_client_blocked_processed_ratio{client}`

### Debug and health metrics
Compatibility alias:
- `adguard_querylog_entries_total`

Explicit processed metric:
- `adguard_querylog_entries_processed_total`

Other debug metrics:
- `adguard_exporter_up`
- `adguard_querylog_up`
- `adguard_querylog_blocked_detected_total`
- `adguard_querylog_nonblocked_detected_total`
- `adguard_querylog_unknown_blocked_state_total`

## Important Metric Semantics
The exporter now treats AdGuard querylog as a rolling snapshot and processes it incrementally using persisted local state.

That means querylog-derived values are exporter-processed cumulative values, not raw snapshot values from a single `querylog` response.

Preferred metrics for new dashboards:
- `adguard_client_queries_processed_total`
- `adguard_client_blocked_processed_total`
- `adguard_client_blocked_processed_ratio`
- `adguard_querylog_entries_processed_total`

Compatibility aliases kept for existing dashboards:
- `adguard_client_queries_total`
- `adguard_client_blocked_total`
- `adguard_client_blocked_ratio`
- `adguard_querylog_entries_total`

These aliases currently expose the same values as the explicit `processed` metrics.

This improves consistency across scrapes, but it also means:
- the exporter depends on persisted local state for continuity
- deleting the state file resets locally processed querylog counters
- restarting the exporter without persisted state will lose incremental history

Global metrics from `/control/stats` are still exposed directly from AdGuard.

## Current Limitations
- Querylog parsing still depends on API field stability across AdGuard versions.
- Querylog remains a snapshot source at the API level.
- Local incremental counters depend on exporter state persistence.
- `unknown_blocked_state` can still affect confidence in per-client blocked ratios.
- Per-client per-domain metrics are not implemented.
- Any `client + domain` metric design must be treated as a Prometheus cardinality risk.

## Configuration
Environment variables:

| Variable | Description | Example |
| --- | --- | --- |
| `ADGUARD_URL` | AdGuard Home base URL | `http://192.168.15.50:3002` |
| `ADGUARD_USERNAME` | AdGuard username | `admin` |
| `ADGUARD_PASSWORD` | AdGuard password | `secret` |
| `REQUEST_TIMEOUT` | API request timeout in seconds | `10` |
| `QUERYLOG_LIMIT` | Number of querylog entries to fetch | `1000` |
| `QUERYLOG_STATE_PATH` | Local file used to persist processed querylog state | `/tmp/adguard_exporter_querylog_state.json` |
| `QUERYLOG_RECENT_FINGERPRINTS_LIMIT` | Number of recent processed fingerprints kept for deduplication | `5000` |
| `EXPORTER_PORT` | HTTP port for the exporter | `9911` |

See [.env.example](/workspace/adguard-exporter/.env.example).

## Running With Docker

```bash
docker compose up -d --build
```

Test the exporter:

```bash
curl http://localhost:9911/
curl http://localhost:9911/metrics
```

## State Persistence Notes
If you want querylog-derived counters to survive container restarts, mount persistent storage for the state file path.

Without persistence:
- global `/control/stats` metrics still work
- querylog-derived local counters restart from zero when the exporter restarts

## Prometheus Example

```yaml
- job_name: adguard-exporter
  static_configs:
    - targets:
        - 192.168.15.50:9911
```

## Grafana Dashboards
This repository includes two Grafana dashboards:

- `dashboards/grafana/adguard_exporter_overview.json`
- `dashboards/grafana/adguard_exporter_devices.json`

Dashboard details:

- `AdGuard Exporter Overview` (`uid: adguard-exporter-overview`)
- `AdGuard Exporter Devices` (`uid: adguard-exporter-devices`)

These dashboards expect a Prometheus datasource and were exported with a Grafana Prometheus datasource input named `DS_PROMETHEUS`.

### Importing The Dashboards
Before importing:

- make sure Grafana already has a working Prometheus datasource
- make sure Prometheus is scraping this exporter
- verify the exporter metrics exist by checking `http://<exporter-host>:9911/metrics`

Import steps in Grafana:

1. Open Grafana.
2. Go to `Dashboards` -> `New` -> `Import`.
3. Click `Upload dashboard JSON file`.
4. Select one of these files from this repo:
   - `dashboards/grafana/adguard_exporter_overview.json`
   - `dashboards/grafana/adguard_exporter_devices.json`
5. When Grafana prompts for the `Prometheus` datasource, choose your Prometheus datasource.
6. Click `Import`.
7. Repeat for the second dashboard file.

Notes:

- If Grafana warns that the dashboard UID already exists, choose whether to overwrite the existing dashboard or change the UID/title during import.
- The dashboards do not require template variables or extra plugins beyond standard Grafana panels and the Prometheus datasource.
- Some panels use the stateful processed querylog metrics such as `adguard_client_queries_processed_total` and `adguard_client_blocked_processed_total`, so querylog state persistence affects what you see after exporter restarts.

### Dashboard Files
If you are running Grafana on a different machine, copy the JSON files from:

- `dashboards/grafana/adguard_exporter_overview.json`
- `dashboards/grafana/adguard_exporter_devices.json`

You can also open the files directly from this repository and paste the JSON into Grafana's import page instead of uploading the files.

## Development
Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest
```

## Useful PromQL
Global:

```promql
adguard_num_dns_queries
adguard_num_blocked_filtering
adguard_blocked_ratio * 100
```

Clients:

```promql
topk(10, adguard_client_queries_processed_total)
topk(10, adguard_client_blocked_processed_total)
topk(10, adguard_client_blocked_processed_ratio * 100)
```

## Engineering Direction
The exporter should keep moving in this direction:
- improve parsing robustness without overengineering
- keep backward compatibility for existing dashboards when possible
- keep label cardinality bounded
- use Prometheus for aggregates and Loki for detailed inspection
- improve error handling and internal observability
- keep the codebase small and maintainable
- keep querylog-derived counters stateful and explicit

## Troubleshooting
If the exporter does not respond:
- verify `ADGUARD_URL`
- verify credentials
- verify container networking

If querylog-derived counters look wrong:
- check the state file path and persistence setup
- check the debug metrics first
- compare exporter output with raw AdGuard querylog behavior
- pay attention to `adguard_querylog_unknown_blocked_state_total`

## License
Personal use / homelab.
