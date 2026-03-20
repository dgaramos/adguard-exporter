# AdGuard Exporter

Exporter customizado em Python para expor métricas do AdGuard Home em
formato Prometheus.

A ideia aqui é simples:

-   autenticar na API do AdGuard
-   coletar dados de `/control/stats`
-   coletar dados de `/control/querylog`
-   transformar isso em métricas Prometheus em `/metrics`
-   visualizar no Grafana via Prometheus

------------------------------------------------------------------------

## O que ele expõe

### Métricas gerais do AdGuard

-   `adguard_num_dns_queries`
-   `adguard_num_blocked_filtering`
-   `adguard_avg_processing_time_seconds`
-   `adguard_blocked_ratio`

### Séries por hora

-   `adguard_dns_queries_hour{hour="..."}`
-   `adguard_blocked_filtering_hour{hour="..."}`

### Top lists

-   `adguard_top_queried_domain_queries{name="..."}`
-   `adguard_top_client_queries{name="..."}`
-   `adguard_top_blocked_domain_queries{name="..."}`
-   `adguard_top_upstream_responses{upstream="..."}`
-   `adguard_top_upstream_avg_time_seconds{upstream="..."}`

### Métricas por client

-   `adguard_client_queries_total{client="..."}`
-   `adguard_client_blocked_total{client="..."}`
-   `adguard_client_blocked_ratio{client="..."}`

### Métricas de saúde/debug

-   `adguard_exporter_up`
-   `adguard_querylog_up`
-   `adguard_querylog_entries_total`
-   `adguard_querylog_blocked_detected_total`
-   `adguard_querylog_nonblocked_detected_total`
-   `adguard_querylog_unknown_blocked_state_total`

------------------------------------------------------------------------

## Como funciona

    AdGuard API (/control/login)
            ↓
    AdGuard API (/control/stats + /control/querylog)
            ↓
    Exporter Python
            ↓
    Prometheus scrapeia /metrics
            ↓
    Grafana consome do Prometheus

------------------------------------------------------------------------

## Estrutura

    .
    ├── app.py
    ├── Dockerfile
    ├── docker-compose.yml
    ├── requirements.txt
    ├── .env.example
    └── README.md

------------------------------------------------------------------------

## Variáveis de ambiente

  Variável           Descrição        Exemplo
  ------------------ ---------------- ---------------------------
  ADGUARD_URL        URL do AdGuard   http://192.168.15.50:3002
  ADGUARD_USERNAME   Usuário          admin
  ADGUARD_PASSWORD   Senha            secret
  REQUEST_TIMEOUT    Timeout          10
  QUERYLOG_LIMIT     Limite logs      1000

------------------------------------------------------------------------

## Execução

    docker compose up -d --build

------------------------------------------------------------------------

## Teste

    curl http://localhost:9911/metrics

------------------------------------------------------------------------

## Prometheus

    - job_name: 'adguard-exporter'
      static_configs:
        - targets: ['192.168.15.50:9911']

------------------------------------------------------------------------

## Queries úteis

### Geral

    adguard_num_dns_queries
    adguard_num_blocked_filtering
    adguard_blocked_ratio * 100

### Clients

    topk(10, adguard_client_queries_total)
    topk(10, adguard_client_blocked_total)
    topk(10, adguard_client_blocked_ratio * 100)

------------------------------------------------------------------------

## Limitações

-   Querylog é snapshot
-   Classificação de blocked não é perfeita
-   Pode haver `unknown`

------------------------------------------------------------------------

## Troubleshooting

### Exporter não responde

-   verificar URL
-   verificar credenciais
-   verificar rede

### Métricas estranhas

-   conferir métricas de debug
-   validar querylog

------------------------------------------------------------------------

## Objetivo

AdGuard → Prometheus → Grafana

------------------------------------------------------------------------

## Licença

Uso pessoal / homelab

