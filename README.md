# LGTM Stack POC (Loki, Grafana, Tempo, Mimir)

An observability stack based on OpenTelemetry (OTel) and the Grafana "LGTM" suite.

## Architecture

- **Loki**: Log aggregation.
- **Grafana**: Visualization and dashboards.
- **Tempo**: Distributed tracing.
- **Mimir**: Scalable Long-term storage for Prometheus metrics.
- **OTel Collector**: Central gateway for receiving and routing telemetry data.
- **MinIO/S3**: Object storage backend for long-term data retention.

## Quick Start

### 1. Prerequisites
- Docker and Docker Compose.
- [uv](https://github.com/astral-sh/uv) (for running the example app).

### 2. Environment Setup
Copy the example environment file and adjust if necessary:
```bash
cp .env.example .env
```

### 2.1 MinIO Setup (Optional)

Follow the MinIO setup instructions below if you want to use MinIO for local development.

### 3. Start the Stack
```bash
docker-compose up -d
```
This starts Loki, Tempo, Mimir, Grafana, the OTel Collector, and a local MinIO instance.

### 4. Run the Example Application
```bash
cd example/fastapi-app
uv sync
uv run python main.py
```
Trigger some data by visiting `http://localhost:8000/process`.

## Configuration: MinIO vs. AWS S3

The stack is currently configured to use **MinIO** for local development.

### Using Local MinIO (Default)

In your `.env` file:
```env
S3_ENDPOINT=host.docker.internal:9000
S3_INSECURE=true
S3_FORCE_PATH_STYLE=true
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
```

Run the container `docker compose up -d` from `example/minio` to start the MinIO instance.

The MinIO instance is running at `http://localhost:9000` with the default credentials `minioadmin/minioadmin`.

Go to the MinIO dashboard, and create the buckets `loki-logs`, `tempo-traces`, and `mimir-metrics`.

### Using AWS S3
To switch to production AWS S3:
1. Update `.env`:
   - `S3_ENDPOINT`: `s3.us-east-1.amazonaws.com` (or your region's endpoint).
   - `S3_INSECURE`: `false`.
   - `S3_FORCE_PATH_STYLE`: `false`.
   - `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY`: Your AWS credentials.
2. Ensure the buckets (`loki-logs`, `tempo-traces`, `mimir-metrics`) exist in your AWS account or update the bucket name variables in `.env`.

### Mimir Metrics & Dashboards

Use the following table to set up your primary observability dashboard. These metrics are exported by the FastAPI application.

| Panel Name | Visualization | Query (PromQL) | Description |
| :--- | :--- | :--- | :--- |
| **Total Request Rate** | Time series | `sum(rate(http_requests_total[$__rate_interval])) by (http_target)` | Real-time traffic per endpoint (Requests/sec). |
| **Error Rate (%)** | Stat | `sum(rate(http_errors_total[$__range])) / sum(rate(http_requests_total[$__range]))` | Percentage of requests resulting in 4xx/5xx errors over the selected time range. |
| **P95 Latency** | Time series | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[$__rate_interval])) by (le))` | 95th percentile response time for all endpoints. |
| **Active Requests** | Gauge | `sum(http_server_active_requests)` | Number of concurrent requests being processed. |
| **Errors by Endpoint** | Bar chart | `sum(increase(http_errors_total[$__range])) by (http_target)` | Total errors grouped by path over the selected time range. |
| **Top 5 Slowest Paths** | Table | `topk(5, sum(rate(http_request_duration_seconds_sum[$__range])) by (http_target) / sum(rate(http_request_duration_seconds_count[$__range])) by (http_target))` | List of endpoints with the highest average latency. |

#### How to Add a Panel
1. Click **+ Add** in the top right of your dashboard -> **Visualization**.
2. Select **Mimir** as the data source.
3. Paste the **Query** from the table above.
4. Set the **Title** to the Panel Name.
5. Select the **Visualization** type from the right sidebar.
6. Click **Save** or **Apply**.

### Loki Logs & Analysis

Loki allows you to query logs using **LogQL**. The stack is configured to automatically label logs with metadata like `service_name` and `deployment_environment`.

#### Key Queries
- **Application Logs** (Visualization: **Logs**)
  - Query: `{service_name="fastapi-service"}`
  - Description: Live stream of all logs from the FastAPI app.
- **Error Log Stream** (Visualization: **Logs**)
  - Query: `{service_name="fastapi-service"} |= "error"`
  - Description: Filtered stream showing only lines containing "error" (case-insensitive).
- **Log Volume** (Visualization: **Time series**)
  - Query: `count_over_time({service_name="fastapi-service"}[$__interval])`
  - Description: Bar chart showing the number of log lines produced per interval.
- **Severity Distribution** (Visualization: **Pie chart**)
  - Query: `sum by (level) (count_over_time({service_name="fastapi-service"}[$__range]))`
  - Description: Breakdown of log levels (INFO, ERROR, WARN) for the selected time range.
- **Error Frequency** (Visualization: **Time series**)
  - Query: `count_over_time({service_name="fastapi-service"} |= "error" [$__interval])`
  - Description: Specifically tracks the rate of error-level logs.

#### How to Add a Log Panel
1. Click **+ Add** -> **Visualization**.
2. Select **Loki** as the data source.
3. Paste one of the **Queries** above.
4. Select the matching **Visualization** type from the right sidebar.

#### Trace Correlation (Loki -> Tempo)
When viewing logs in the **Explore** tab or a **Logs** panel:
1. Click on a log line to expand it.
2. Look for the `trace_id` field.
3. Click the **Tempo** button next to the ID to instantly see the full distributed trace for that specific log entry.

### Advanced Observability Patterns

Beyond basic metrics, you can leverage the full power of the LGTM stack with these advanced patterns:

#### 1. The RED Method (Rate, Errors, Duration)
Industry standard for request-driven services:
- **Rate**: `sum(rate(http_requests_total[$__rate_interval]))`
- **Errors**: `sum(rate(http_errors_total[$__rate_interval]))`
- **Duration**: `histogram_quantile(0.9, sum(rate(http_request_duration_seconds_bucket[$__rate_interval])) by (le))`

#### 2. Latency Heatmap (Visualization: Heatmap)
Shows the *distribution* of latency. Large "blobs" at higher buckets indicate sporadic performance issues.
- **Query**: `sum(rate(http_request_duration_seconds_bucket[$__rate_interval])) by (le)`
- **Format**: Time series
- **Heatmap setting**: In the visualization settings, ensure "Calculate from buckets" is enabled.

#### 3. Log Severity Distribution (select Loki datasource)
Monitor the health of your application logs by severity.
- **Query**: `sum by (level) (count_over_time({service_name="fastapi-service"} [$__range]))`
- **Visualization**: Time series (Stacked) or Bar gauge.

#### 4. Apdex Score (Performance Index)
A single score (0 to 1) representing user satisfaction (e.g., target = 0.5s).
- **Query**: `(sum(rate(http_request_duration_seconds_bucket{le="0.5"}[$__range])) + sum(rate(http_request_duration_seconds_bucket{le="1.0"}[$__range])) / 2) / sum(rate(http_request_duration_seconds_count[$__range]))`

#### 5. Resource Attribute Grouping
Compare performance across different deployments or host types.
- **Query**: `sum(rate(http_requests_total[$__rate_interval])) by (service_version, deployment_environment)`

> [!TIP]
> **Dynamic Time Ranges**: Instead of hardcoding `[5m]`, use Grafana global variables:
> - **`[$__range]`**: Adjusts to the exact time period selected in the dashboard picker (e.g., Last 1 hour). Use this for total counts (with `increase()`) or "Stat" panels.
> - **`[$__rate_interval]`**: Automatically calculates the best interval for `rate()` based on the graph's time range and resolution. Use this for Time series graphs.

## Debugging Tips

- **Unhealthy Ring**: If Mimir/Loki report ring issues, ensure `replication_factor` is set to `1` in the YAML configs for single-node setups.
- **Log Ingestion**: Check the OTel Collector logs (`docker logs otel-collector`) to see if data is being received and exported correctly.
- **S3 Connectivity**: Ensure the S3 endpoint is reachable from *within* the Docker containers. On MacOS, `host.docker.internal` is used to reach the host's port 9000.
