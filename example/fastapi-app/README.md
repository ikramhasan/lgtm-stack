# FastAPI OTel LGTM Stack Test

This is a demonstration of FastAPI integrated with the LGTM (Loki, Grafana, Tempo, Mimir) stack using OpenTelemetry.

## Setup

1.  Ensure the LGTM stack is running (using the root `docker-compose.yml`).
2.  Install dependencies:
    ```bash
    uv sync
    ```
3.  Run the application:
    ```bash
    uv run python main.py
    ```

## Endpoints

- `GET /`: Basic endpoint with logging.
- `GET /process`: Triggers nested traces and data processing logs.
- `GET /error`: Triggers an intentional 500 error and error logs.
- `GET /random-error`: Randomly triggers a 400 error.

## OpenTelemetry Exports

- **Traces**: Sent to Tempo (via OTel Collector).
- **Metrics**: Sent to Mimir (via OTel Collector).
- **Logs**: Sent to Loki (via OTel Collector).
