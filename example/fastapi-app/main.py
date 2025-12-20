import logging
import os
import random
import time
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

# Load environment variables
load_dotenv()

# Service metadata
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "fastapi-service")
ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

resource = Resource.create({
    "service.name": SERVICE_NAME,
    "service.version": "1.0.0",
    "deployment.environment": "production"
})

# Tracing setup
tracer_provider = TracerProvider(resource=resource)
span_exporter = OTLPSpanExporter(endpoint=ENDPOINT, insecure=True)
tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(__name__)

# Metrics setup
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=ENDPOINT, insecure=True),
    export_interval_millis=1000
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

# Logs setup
logger_provider = LoggerProvider(resource=resource)
log_exporter = OTLPLogExporter(endpoint=ENDPOINT, insecure=True)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)

# Attach OTLP handler to root logger
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Auto-instrument logging to inject trace IDs into logs
LoggingInstrumentor().instrument(set_logging_format=True)

app = FastAPI(title="LGTM Stack Test API")

# Custom metrics
request_counter = meter.create_counter(
    "http_requests_total",
    description="Total number of HTTP requests",
    unit="1",
)
error_counter = meter.create_counter(
    "http_errors_total",
    description="Total number of HTTP errors",
    unit="1",
)
request_duration = meter.create_histogram(
    "http_request_duration_seconds",
    description="HTTP request duration in seconds",
    unit="s",
)

@app.middleware("http")
async def add_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    method = request.method
    path = request.url.path
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    status_code = str(response.status_code)
    
    attributes = {
        "http.method": method,
        "http.target": path,
        "http.status_code": status_code,
    }
    
    request_counter.add(1, attributes)
    request_duration.record(duration, attributes)
    
    if response.status_code >= 400:
        error_counter.add(1, attributes)
        
    return response

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI server starting up...")

@app.get("/")
async def root():
    with tracer.start_as_current_span("root_handler"):
        logger.info("Root endpoint called")
        return {"message": "Welcome to the LGTM Stack Test API"}

@app.get("/process")
async def process_data():
    with tracer.start_as_current_span("process_data"):
        logger.info("Starting data processing")
        await sub_process_1()
        await sub_process_2()
        logger.info("Data processing completed")
        return {"status": "success"}

async def sub_process_1():
    with tracer.start_as_current_span("sub_process_1"):
        logger.info("Executing sub_process_1")
        time.sleep(random.uniform(0.1, 0.5))
        logger.info("sub_process_1 completed")

async def sub_process_2():
    with tracer.start_as_current_span("sub_process_2"):
        logger.info("Executing sub_process_2")
        time.sleep(random.uniform(0.1, 0.3))
        # Deeply nested span
        with tracer.start_as_current_span("deep_nested_task"):
            logger.info("Doing some deep work")
            time.sleep(0.1)
        logger.info("sub_process_2 completed")

@app.get("/error")
async def trigger_error():
    with tracer.start_as_current_span("error_trigger"):
        logger.error("An intentional error occurred!")
        raise HTTPException(status_code=500, detail="Intentional server error")

@app.get("/random-error")
async def random_error():
    if random.random() < 0.5:
        logger.warning("Random failure probability triggered")
        raise HTTPException(status_code=400, detail="Random bad request")
    return {"status": "ok"}

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
