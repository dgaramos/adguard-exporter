# adguard_exporter

A custom Python Prometheus exporter for AdGuard Home.

This project exists because AdGuard Home's native Prometheus metrics are not enough for the level of observability needed in this homelab setup. The exporter collects data from the AdGuard API, reshapes it into Prometheus metrics, and makes it easy to build Grafana dashboards around DNS usage, blocking behavior, and client-level visibility.

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
- exposes Prometheus metrics at `/metrics`

## Project Structure

```text
.
├── adguard_exporter/
│   ├── clients/
│   │   └── adguard.py
│   ├── metrics/
│   │   └── exporter.py
│   ├── parsers/
│   │   └── querylog.py
│   ├── __init__.py
│   ├── app.py
│   └── config.py
├── tests/
│   ├── test_app.py
│   └── test_querylog_parser.py
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
- `adguard_client_queries_total{client}`
- `adguard_client_blocked_total{client}`
- `adguard_client_blocked_ratio{client}`

### Debug and health metrics
- `adguard_exporter_up`
- `adguard_querylog_up`
- `adguard_querylog_entries_total`
- `adguard_querylog_blocked_detected_total`
- `adguard_querylog_nonblocked_detected_total`
- `adguard_querylog_unknown_blocked_state_total`

## Important Metric Semantics
Some metrics are derived from a querylog snapshot, not from a true historical counter stream.

That means:
- `adguard_client_queries_total`
- `adguard_client_blocked_total`
- `adguard_client_blocked_ratio`

are snapshot-based values built from the current AdGuard querylog response. They are useful, but they should not be treated as perfect monotonic counters.

## Current Limitations
- Querylog parsing is still heuristic.
- AdGuard querylog shape is not fully stable across versions.
- `unknown_blocked_state` can be high enough to affect confidence in per-client blocked ratios.
- Querylog is a snapshot, not a complete historical source.
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

## Prometheus Example

```yaml
- job_name: adguard-exporter
  static_configs:
    - targets:
        - 192.168.15.50:9911
```

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
topk(10, adguard_client_queries_total)
topk(10, adguard_client_blocked_total)
topk(10, adguard_client_blocked_ratio * 100)
```

## Engineering Direction
The exporter should keep moving in this direction:
- improve parsing robustness without overengineering
- keep backward compatibility for existing dashboards when possible
- keep label cardinality bounded
- use Prometheus for aggregates and Loki for detailed inspection
- improve error handling and internal observability
- keep the codebase small and maintainable

## Troubleshooting
If the exporter does not respond:
- verify `ADGUARD_URL`
- verify credentials
- verify container networking

If the metrics look wrong:
- check the debug metrics first
- compare exporter output with raw AdGuard querylog behavior
- pay attention to `adguard_querylog_unknown_blocked_state_total`

## License
Personal use / homelab.
