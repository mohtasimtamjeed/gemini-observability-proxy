# Observable, Rate-Limited Gemini API Proxy

A production-grade AI gateway wrapping the Google Gemini API with token telemetry, upstream quota protection, in-memory SHA-256 caching, and Infrastructure-as-Code provisioning.

---

## Architecture Overview


```text
                      +-------------------+
                      |   Client / cURL   |
                      +---------+---------+
                                |
                                | HTTP POST /generate
                                v
+-------------------------------------------------------------------+
|  Docker Bridge Network (`gemini_proxy_network`)                   |
|                                                                   |
|   +-----------------------------------------------------------+   |
|   |  FastAPI Gateway (`gemini-proxy:8000`)                    |   |
|   |  - Non-Root Security Context (UID 10000)                  |   |
|   |  - Sliding-Window Rate Limiter (10 req/60s)               |   |
|   |  - SHA-256 Response Cache (TTL 1hr)                       |   |
|   |  - Async Non-Blocking Gemini SDK Client                   |   |
|   |  - Native Docker HEALTHCHECK (/health)                    |   |
|   +-----------------------------+-----------------------------+   |
|                                 |                                 |
|                                 | Scrapes /metrics every 5s       |
|                                 v                                 |
|   +-----------------------------------------------------------+   |
|   |  Prometheus Monitoring (`prometheus:9090`)                |   |
|   |  - Pull-based OpenMetrics TSDB ingestion                  |   |
|   |  - Custom Counters: Tokens, Cache Efficacy, p95 Latency   |   |
|   +-----------------------------------------------------------+   |
+-------------------------------------------------------------------+
                                ^
                                | Provisioned via
+-------------------------------+-----------------------------------+
|                  Terraform Infrastructure as Code                 |
|       (kreuzwerker/docker: Networks, Images, Volumes, Tasks)      |
+-------------------------------------------------------------------+


```
---

## Key Engineering Guardrails

1. **Deterministic SHA-256 Response Caching:**
   - Incoming prompts and model identifiers are hashed using SHA-256 to create deterministic 64-character lookup keys.
   - Cached entries honor a 1-hour Time-To-Live (TTL), reducing redundant downstream token costs by 100% on repeated queries and serving responses in under 5ms.
   - Responses advertise cache status via standard `X-Cache: HIT` or `X-Cache: MISS` headers.

2. **Sliding-Window Rate Limiting:**
   - Enforces an in-memory sliding-window threshold (10 requests / 60 seconds per client IP) using eviction deques.
   - Protects upstream Gemini quota pools and returns HTTP `429 Too Many Requests` with a dynamic `Retry-After` header without invoking downstream network I/O.

3. **Domain-Specific Observability:**
   - Tracks standard HTTP Golden Signals (request duration histograms, throughput, status codes) via `prometheus-fastapi-instrumentator`.
   - Exports custom OpenMetrics counters:
     - `gemini_tokens_total{model="...", type="prompt|completion"}`
     - `gemini_cache_events_total{status="hit|miss"}`

4. **Hardened Containerization:**
   - Multi-stage build based on `python:3.12-slim` isolating build wheels from the runtime container.
   - Enforces a non-root system user (`appuser`, UID 10000) to mitigate container breakout vectors.
   - Contains a native Docker `HEALTHCHECK` checking the `/health` endpoint every 15 seconds.

5. **Infrastructure as Code (IaC):**
   - Fully automated provisioning of networks, bind volumes, image lifecycle, and container tasks using Terraform (`kreuzwerker/docker`).

---

## Quickstart

### Prerequisites

- Docker Engine / Docker Desktop
- Terraform (>= 1.5.0)
- Google Gemini API Key

### 1. Clone & Set Environment Variables

```bash
git clone https://github.com/your-username/gemini-observability-proxy.git
cd gemini-observability-proxy
```

# Create your .env file

```bash
echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
```

### 2. Build the Production Image

```bash
docker build -t gemini-proxy:v1 .
```

### 3. Provision Infrastructure via Terraform

```bash
cd terraform
```

# Supply the API key via environment variable or terraform.tfvars

```bash
export TF_VAR_gemini_api_key=$(grep -v '^#' ../.env | grep 'GEMINI_API_KEY=' | cut -d '=' -f2 | tr -d ' "\r\n')

terraform init
terraform apply -auto-approve
```
---

## Verification & Monitoring

### Send a Prompt

```bash
curl -i -X POST http://localhost:8000/generate \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Explain gravitational waves in three words."}'
```

### Access Prometheus Dashboards

Open `http://localhost:9090` and evaluate:

- Token Consumption:

```text
  gemini_tokens_total
```

- Cache Efficiency Ratio (%):

```text
  sum(gemini_cache_events_total{status="hit"}) / sum(gemini_cache_events_total) * 100
```

- Traffic Throughput by HTTP Status:
  
```text
  sum by (status) (http_requests_total{handler="/generate"})
```

---

## Teardown

To destroy all running containers, networks, and provisioned state:

```bash
cd terraform
terraform destroy -auto-approve
```