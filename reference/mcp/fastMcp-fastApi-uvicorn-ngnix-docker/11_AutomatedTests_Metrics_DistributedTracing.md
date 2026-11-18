# Increment 11 — Automated Tests, Metrics, and Distributed Tracing

## Goal

Build a test pyramid and production-style observability:

```text
                         ┌───────────────┐
                         │ End-to-end    │  Few, slow, realistic
                         │ Docker + TLS  │
                     ┌───┴───────────────┴───┐
                     │ MCP contract tests    │
                     │ Tools/resources/auth  │
                 ┌───┴───────────────────────┴───┐
                 │ Repository + ASGI integration │
             ┌───┴───────────────────────────────┴───┐
             │ Service and domain unit tests         │
             └───────────────────────────────────────┘
```

Observability becomes:

```text
MCP request
    │
    ├── Structured logs ──► stdout
    ├── Metrics ──────────► Prometheus
    └── Traces ───────────► Jaeger
```

FastMCP recommends its in-memory client for deterministic server tests because it avoids subprocess and network complexity. It also provides native OpenTelemetry spans for tool, resource, prompt, and task operations once an OpenTelemetry SDK is configured. [FastMCP](https://gofastmcp.com/servers/testing)

---

# 1. Add Dependencies

Runtime observability dependencies:

```bash
uv add \
  prometheus-client \
  opentelemetry-distro \
  opentelemetry-sdk \
  opentelemetry-exporter-otlp
```

Testing dependencies:

```bash
uv add --dev \
  pytest \
  pytest-asyncio
```

`uv add --dev` records packages in the standardized development dependency group rather than the published runtime requirements. FastMCP’s current testing guide uses `pytest-asyncio` and recommends automatic asyncio mode. [Astral Docs](https://docs.astral.sh/uv/concepts/projects/dependencies/?utm_source=chatgpt.com)

---

# 2. Configure Pytest

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

addopts = [
    "-ra",
    "--strict-config",
    "--strict-markers",
]

markers = [
    "integration: tests involving real infrastructure adapters",
    "telemetry: tests asserting emitted telemetry",
    "e2e: tests requiring the running Docker Compose stack",
]
```

Create this structure:

```text
tests/
├── conftest.py
├── unit/
│   └── test_service.py
├── integration/
│   ├── test_repository.py
│   ├── test_application.py
│   └── test_metrics.py
├── protocol/
│   └── test_mcp.py
├── telemetry/
│   └── test_tracing.py
└── e2e/
    └── test_secure_stack.py
```

Fixtures centralize reusable setup and use `yield` teardown so cleanup runs after the test, including when an assertion fails. [pytest](https://docs.pytest.org/en/stable/how-to/fixtures.html)

---

# 3. Make MCP Authorization Optional for In-Memory Tests

Our production MCP server requires bearer-token scopes. In-memory protocol tests should not need to reproduce the HTTP authentication transport.

Update the factory signature in `server.py`:

```python
from __future__ import annotations

import json
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ResourceError, ToolError
from fastmcp.server.auth import require_scopes

from errors import ArithmeticServiceError
from service import ArithmeticService


def create_mcp(
    service: ArithmeticService,
    auth_provider: Any = None,
    *,
    enforce_authorization: bool = True,
) -> FastMCP:
    """Create the MCP server.

    Production enables authentication and scope authorization.
    In-memory protocol tests may disable authorization while testing
    component schemas, dispatch, serialization, and error translation.
    """

    read_authorization = (
        require_scopes("calc:read")
        if enforce_authorization
        else None
    )

    write_authorization = (
        require_scopes("calc:write")
        if enforce_authorization
        else None
    )

    mcp = FastMCP(
        name="First Principles MCP",
        instructions=(
            "Use arithmetic tools to perform calculations. "
            "Use calculation-history resources when historical "
            "context is required."
        ),
        auth=auth_provider,
        mask_error_details=True,
    )

    @mcp.tool(auth=write_authorization)
    async def add(
        a: int,
        b: int,
        ctx: Context,
    ) -> dict:
        """Add two integers and persist the calculation."""

        try:
            record = await service.add(a, b)
        except ArithmeticServiceError as exc:
            raise ToolError(str(exc)) from exc

        return record.model_dump(mode="json")

    @mcp.tool(auth=write_authorization)
    async def multiply(
        a: int,
        b: int,
        ctx: Context,
    ) -> dict:
        """Multiply two integers and persist the calculation."""

        try:
            record = await service.multiply(a, b)
        except ArithmeticServiceError as exc:
            raise ToolError(str(exc)) from exc

        return record.model_dump(mode="json")

    @mcp.resource(
        uri="history://calculations/recent/{limit}",
        name="RecentCalculations",
        title="Recent Arithmetic Calculations",
        description="Return recently persisted calculations.",
        mime_type="application/json",
        annotations={
            "readOnlyHint": True,
            "idempotentHint": True,
        },
        auth=read_authorization,
    )
    async def recent_calculations(
        limit: int,
        ctx: Context,
    ) -> str:
        try:
            records = await service.recent_calculations(limit)
        except ArithmeticServiceError as exc:
            raise ResourceError(str(exc)) from exc

        return json.dumps(
            [
                record.model_dump(mode="json")
                for record in records
            ],
            indent=2,
        )

    @mcp.prompt(
        name="explain_arithmetic",
        title="Explain an Arithmetic Calculation",
        description="Create instructions for explaining a calculation.",
        auth=read_authorization,
    )
    def explain_arithmetic(
        operation: str,
        a: int,
        b: int,
        audience: str = "beginner",
    ) -> str:
        return (
            f"Explain how to {operation} {a} and {b} "
            f"to a {audience} audience.\n\n"
            "Show each step, explain the reasoning, state the final "
            "answer, and provide one similar practice problem."
        )

    return mcp
```

Production remains unchanged:

```python
mcp = create_mcp(
    service,
    auth_provider,
    enforce_authorization=True,
)
```

Tests use:

```python
mcp = create_mcp(
    service,
    enforce_authorization=False,
)
```

This is not an authentication test bypass in production. It is a factory option used only to isolate MCP contract behavior from HTTP credential transport.

---

# 4. Shared Test Fixtures

Create `tests/conftest.py`:

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastmcp import Client

from app import create_application
from repository import (
    InMemoryCalculationRepository,
    SQLiteCalculationRepository,
)
from server import create_mcp
from service import ArithmeticService


@pytest.fixture
def in_memory_repository() -> InMemoryCalculationRepository:
    return InMemoryCalculationRepository()


@pytest.fixture
def service(
    in_memory_repository: InMemoryCalculationRepository,
) -> ArithmeticService:
    return ArithmeticService(in_memory_repository)


@pytest.fixture
async def sqlite_repository(
    tmp_path: Path,
) -> AsyncIterator[SQLiteCalculationRepository]:
    repository = SQLiteCalculationRepository(
        tmp_path / "calculations.db"
    )

    await repository.start()

    try:
        yield repository
    finally:
        await repository.close()


@pytest.fixture
async def mcp_client(
    service: ArithmeticService,
) -> AsyncIterator[Client]:
    mcp = create_mcp(
        service,
        enforce_authorization=False,
    )

    async with Client(mcp) as client:
        yield client


@pytest.fixture
def application(tmp_path: Path):
    return create_application(
        database_path=tmp_path / "application.db",
        read_token="test-reader-token",
        write_token="test-writer-token",
    )
```

The in-memory FastMCP transport exercises discovery, invocation, serialization, context creation, and error translation without subprocess or socket behavior. [FastMCP](https://gofastmcp.com/clients/client)

---

# 5. Unit Tests

Create `tests/unit/test_service.py`:

```python
from __future__ import annotations

import pytest

from errors import (
    InvalidHistoryLimitError,
    OperandOutOfRangeError,
)
from service import ArithmeticService


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (0, 0, 0),
        (20, 22, 42),
        (-5, 8, 3),
        (-10, -20, -30),
    ],
)
async def test_add(
    service: ArithmeticService,
    a: int,
    b: int,
    expected: int,
) -> None:
    record = await service.add(a, b)

    assert record.operation == "add"
    assert record.a == a
    assert record.b == b
    assert record.result == expected


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (0, 100, 0),
        (6, 7, 42),
        (-4, 8, -32),
        (-3, -9, 27),
    ],
)
async def test_multiply(
    service: ArithmeticService,
    a: int,
    b: int,
    expected: int,
) -> None:
    record = await service.multiply(a, b)

    assert record.operation == "multiply"
    assert record.result == expected


async def test_history_is_newest_first(
    service: ArithmeticService,
) -> None:
    first = await service.add(1, 2)
    second = await service.multiply(3, 4)

    history = await service.recent_calculations(10)

    assert [record.id for record in history] == [
        second.id,
        first.id,
    ]


async def test_rejects_large_operand(
    service: ArithmeticService,
) -> None:
    with pytest.raises(
        OperandOutOfRangeError,
        match="must not exceed",
    ):
        await service.add(1_000_001, 1)


@pytest.mark.parametrize(
    "limit",
    [
        0,
        -1,
        101,
        10_000,
    ],
)
async def test_rejects_invalid_history_limit(
    service: ArithmeticService,
    limit: int,
) -> None:
    with pytest.raises(InvalidHistoryLimitError):
        await service.recent_calculations(limit)
```

These are fast because they do not involve:

- SQLite
- MCP
- HTTP
- TLS
- Docker
- Authentication

Professional wording:

> “Unit tests verify application invariants against an in-memory outbound adapter.”

---

# 6. Repository Integration Tests

Create `tests/integration/test_repository.py`:

```python
from __future__ import annotations

import pytest

from repository import SQLiteCalculationRepository


pytestmark = pytest.mark.integration


async def test_save_and_read(
    sqlite_repository: SQLiteCalculationRepository,
) -> None:
    saved = await sqlite_repository.save(
        operation="add",
        a=20,
        b=22,
        result=42,
    )

    history = await sqlite_repository.list_recent(10)

    assert len(history) == 1
    assert history[0] == saved


async def test_records_survive_connection_restart(
    tmp_path,
) -> None:
    database_path = tmp_path / "persistent.db"

    first_repository = SQLiteCalculationRepository(
        database_path
    )

    await first_repository.start()

    await first_repository.save(
        operation="multiply",
        a=6,
        b=7,
        result=42,
    )

    await first_repository.close()

    second_repository = SQLiteCalculationRepository(
        database_path
    )

    await second_repository.start()

    try:
        history = await second_repository.list_recent(10)

        assert len(history) == 1
        assert history[0].result == 42
    finally:
        await second_repository.close()


async def test_use_before_start_fails(
    tmp_path,
) -> None:
    repository = SQLiteCalculationRepository(
        tmp_path / "not-started.db"
    )

    with pytest.raises(
        RuntimeError,
        match="has not been started",
    ):
        await repository.list_recent(10)
```

This layer verifies real SQL, transactions, persistence, schema creation, and connection lifecycle.

---

# 7. MCP Contract Tests

Create `tests/protocol/test_mcp.py`:

```python
from __future__ import annotations

import json

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError


async def test_component_discovery(
    mcp_client: Client,
) -> None:
    tools = await mcp_client.list_tools()
    templates = await mcp_client.list_resource_templates()
    prompts = await mcp_client.list_prompts()

    assert {tool.name for tool in tools} == {
        "add",
        "multiply",
    }

    assert {
        template.name
        for template in templates
    } == {
        "RecentCalculations",
    }

    assert {
        prompt.name
        for prompt in prompts
    } == {
        "explain_arithmetic",
    }


async def test_tool_call(
    mcp_client: Client,
) -> None:
    result = await mcp_client.call_tool(
        "add",
        {
            "a": 20,
            "b": 22,
        },
    )

    assert result.data["operation"] == "add"
    assert result.data["result"] == 42


async def test_resource_read(
    mcp_client: Client,
) -> None:
    await mcp_client.call_tool(
        "multiply",
        {
            "a": 6,
            "b": 7,
        },
    )

    content = await mcp_client.read_resource(
        "history://calculations/recent/10"
    )

    payload = json.loads(content[0].text)

    assert payload[0]["operation"] == "multiply"
    assert payload[0]["result"] == 42


async def test_prompt_rendering(
    mcp_client: Client,
) -> None:
    result = await mcp_client.get_prompt(
        "explain_arithmetic",
        {
            "operation": "multiply",
            "a": 6,
            "b": 7,
            "audience": "beginner",
        },
    )

    assert len(result.messages) == 1
    assert "multiply 6 and 7" in result.messages[0].content.text


async def test_business_error_becomes_tool_error(
    mcp_client: Client,
) -> None:
    with pytest.raises(
        ToolError,
        match="must not exceed",
    ):
        await mcp_client.call_tool(
            "add",
            {
                "a": 2_000_000,
                "b": 1,
            },
        )
```

These are **contract tests** because they assert the externally observable MCP surface rather than only Python implementation details.

---

# 8. Add Prometheus Metrics

Create `metrics.py`:

```python
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, MutableMapping

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    GCCollector,
    Histogram,
    PlatformCollector,
    ProcessCollector,
)


@dataclass(frozen=True)
class ApplicationMetrics:
    registry: CollectorRegistry
    requests: Counter
    duration: Histogram
    in_progress: Gauge


def create_application_metrics() -> ApplicationMetrics:
    # A registry per application factory prevents metric-registration
    # collisions when tests construct several FastAPI applications.
    registry = CollectorRegistry()

    GCCollector(registry=registry)
    PlatformCollector(registry=registry)
    ProcessCollector(registry=registry)

    requests = Counter(
        "mcp_http_requests",
        "Completed HTTP requests.",
        labelnames=[
            "method",
            "endpoint",
            "status_class",
        ],
        registry=registry,
    )

    duration = Histogram(
        "mcp_http_request_duration_seconds",
        "HTTP request duration in seconds.",
        labelnames=[
            "method",
            "endpoint",
        ],
        buckets=(
            0.005,
            0.01,
            0.025,
            0.05,
            0.1,
            0.25,
            0.5,
            1,
            2.5,
            5,
            10,
            30,
        ),
        registry=registry,
    )

    in_progress = Gauge(
        "mcp_http_requests_in_progress",
        "HTTP requests currently executing.",
        labelnames=[
            "method",
            "endpoint",
        ],
        registry=registry,
    )

    return ApplicationMetrics(
        registry=registry,
        requests=requests,
        duration=duration,
        in_progress=in_progress,
    )


def classify_endpoint(path: str) -> str:
    """Map unbounded request paths into bounded metric labels."""

    if path.startswith("/mcp"):
        return "mcp"

    if path == "/health/live":
        return "health_live"

    if path == "/health/ready":
        return "health_ready"

    if path.startswith("/internal/metrics"):
        return "metrics"

    return "other"


class MetricsMiddleware:
    def __init__(
        self,
        app: Callable[..., Awaitable[None]],
        metrics: ApplicationMetrics,
    ) -> None:
        self._app = app
        self._metrics = metrics

    async def __call__(
        self,
        scope: MutableMapping[str, Any],
        receive: Callable[..., Awaitable[Any]],
        send: Callable[..., Awaitable[None]],
    ) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        method = str(scope.get("method", "UNKNOWN"))
        endpoint = classify_endpoint(
            str(scope.get("path", ""))
        )

        # Do not cause each Prometheus scrape to modify the metrics
        # being scraped.
        if endpoint == "metrics":
            await self._app(scope, receive, send)
            return

        status_code = 500
        started_at = time.perf_counter()

        labels = {
            "method": method,
            "endpoint": endpoint,
        }

        self._metrics.in_progress.labels(**labels).inc()

        async def send_wrapper(message: MutableMapping[str, Any]):
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = int(message["status"])

            await send(message)

        try:
            await self._app(
                scope,
                receive,
                send_wrapper,
            )
        finally:
            elapsed = time.perf_counter() - started_at

            self._metrics.in_progress.labels(**labels).dec()

            self._metrics.duration.labels(
                **labels,
            ).observe(elapsed)

            self._metrics.requests.labels(
                method=method,
                endpoint=endpoint,
                status_class=f"{status_code // 100}xx",
            ).inc()
```

Prometheus counters are suited to monotonically increasing event counts, gauges to values that move up and down, and histograms to latency distributions. The official Python client also provides an ASGI application for exposing a metrics registry. [Prometheus](https://prometheus.github.io/client_python/instrumenting/)

## Avoid high-cardinality labels

Do not label metrics with:

```text
request_id
user_id
session_id
resource URI
raw tool arguments
database record ID
```

These values can create effectively unbounded time-series counts.

Our endpoint label is restricted to:

```text
mcp
health_live
health_ready
metrics
other
```

Professional wording:

> “Metric dimensions must have bounded cardinality.”

---

# 9. Mount the Metrics Endpoint

Add imports to `app.py`:

```python
from prometheus_client import make_asgi_app

from metrics import (
    MetricsMiddleware,
    create_application_metrics,
)
```

After constructing the FastAPI application:

```python
application_metrics = create_application_metrics()

application.state.metrics = application_metrics

application.add_middleware(
    MetricsMiddleware,
    metrics=application_metrics,
)

metrics_app = make_asgi_app(
    registry=application_metrics.registry,
)

application.mount(
    "/internal/metrics",
    metrics_app,
)
```

Keep `/internal/metrics` out of Nginx’s allowed routes. Prometheus will scrape it through the private Docker backend network.

---

# 10. Test Metrics

Create `tests/integration/test_metrics.py`:

```python
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.integration


def test_health_request_is_recorded(
    application,
) -> None:
    with TestClient(application) as client:
        response = client.get("/health/live")

        assert response.status_code == 200

        metrics = client.get("/internal/metrics")

        assert metrics.status_code == 200

        body = metrics.text

        assert "mcp_http_requests_total" in body
        assert 'endpoint="health_live"' in body
        assert 'status_class="2xx"' in body
```

---

# 11. Add Trace IDs to Structured Logs

Update `observability.py`.

Add:

```python
from opentelemetry import trace
```

Inside `JsonFormatter.format()`:

```python
span_context = trace.get_current_span().get_span_context()

if span_context.is_valid:
    payload["trace_id"] = format(
        span_context.trace_id,
        "032x",
    )

    payload["span_id"] = format(
        span_context.span_id,
        "016x",
    )
```

A log record can now contain:

```json
{
  "request_id": "4aeecf7745404b26af13d136bcdfa341",
  "trace_id": "45ec0a393e287b673c200cd1940fe7a8",
  "span_id": "8a9be6319ce1cf21",
  "message": "http_request_complete"
}
```

These identifiers serve different purposes:

| Identifier | Scope |
|---|---|
| Request ID | One edge HTTP request |
| Trace ID | Entire distributed operation |
| Span ID | One timed operation inside the trace |

---

# 12. Add Repository Spans

Add to `repository.py`:

```python
from opentelemetry import trace


tracer = trace.get_tracer(
    "mcp_service.repository"
)
```

Wrap `save()`:

```python
async def save(
    self,
    operation: Operation,
    a: int,
    b: int,
    result: int,
) -> CalculationRecord:
    with tracer.start_as_current_span(
        "calculation_repository.save"
    ) as span:
        span.set_attribute(
            "app.calculation.operation",
            operation,
        )

        return await self._save_record(
            operation=operation,
            a=a,
            b=b,
            result=result,
        )
```

Move the original implementation into `_save_record()`:

```python
async def _save_record(
    self,
    operation: Operation,
    a: int,
    b: int,
    result: int,
) -> CalculationRecord:
    connection = self._require_connection()
    created_at = datetime.now(timezone.utc)

    async with self._write_lock:
        try:
            cursor = await connection.execute(
                """
                INSERT INTO calculations (
                    operation,
                    operand_a,
                    operand_b,
                    result,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    operation,
                    a,
                    b,
                    result,
                    created_at.isoformat(),
                ),
            )

            try:
                record_id = cursor.lastrowid
            finally:
                await cursor.close()

            await connection.commit()
        except BaseException:
            await connection.rollback()
            raise

    if record_id is None:
        raise RuntimeError(
            "SQLite did not return a calculation identifier."
        )

    return CalculationRecord(
        id=record_id,
        operation=operation,
        a=a,
        b=b,
        result=result,
        created_at=created_at,
    )
```

Wrap history reads similarly:

```python
async def list_recent(
    self,
    limit: int,
) -> list[CalculationRecord]:
    with tracer.start_as_current_span(
        "calculation_repository.list_recent"
    ) as span:
        span.set_attribute(
            "app.history.limit",
            limit,
        )

        return await self._list_recent(limit)
```

Do not attach these as trace attributes:

```text
Bearer token
Database path
Raw prompt
Complete customer input
Secret values
```

Custom spans are most useful around external calls and expensive or difficult-to-debug work; FastMCP recommends avoiding spans around every trivial helper function. [FastMCP](https://gofastmcp.com/servers/telemetry)

---

# 13. Enable OpenTelemetry at Process Startup

FastMCP’s instrumentation uses the OpenTelemetry API automatically, but spans are no-ops until an SDK and exporter are configured. `opentelemetry-instrument` configures the SDK before importing the application, which is the correct initialization order. [FastMCP](https://gofastmcp.com/servers/telemetry)

Update the Dockerfile command:

```dockerfile
CMD [
    "opentelemetry-instrument",
    "uvicorn",
    "app:create_application",
    "--factory",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--workers", "1",
    "--lifespan", "on",
    "--proxy-headers",
    "--forwarded-allow-ips", "172.28.0.10",
    "--timeout-keep-alive", "5",
    "--timeout-graceful-shutdown", "20",
    "--log-level", "info",
    "--no-access-log"
]
```

Add to the application environment in `compose.yaml`:

```yaml
environment:
  CALC_DB_PATH: /data/calculations.db
  MCP_READ_TOKEN_FILE: /run/secrets/mcp_read_token
  MCP_WRITE_TOKEN_FILE: /run/secrets/mcp_write_token

  FASTMCP_TELEMETRY_MODE: native

  OTEL_SERVICE_NAME: mcp-first-principles
  OTEL_TRACES_EXPORTER: otlp
  OTEL_METRICS_EXPORTER: none
  OTEL_LOGS_EXPORTER: none

  OTEL_EXPORTER_OTLP_ENDPOINT: http://jaeger:4318
  OTEL_EXPORTER_OTLP_PROTOCOL: http/protobuf

  # Suitable for this local learning stack.
  # Production sampling must follow traffic and cost requirements.
  OTEL_TRACES_SAMPLER: parentbased_always_on
```

FastMCP’s native mode emits its own MCP span hierarchy and propagates trace context. If another MCP-aware instrumentation layer later creates duplicate MCP spans, use `propagation_only` rather than blindly disabling context propagation. [FastMCP](https://gofastmcp.com/servers/telemetry)

---

# 14. Add Prometheus Configuration

Create:

```text
prometheus/
└── prometheus.yml
```

Create `prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 5s
  evaluation_interval: 5s

scrape_configs:
  - job_name: mcp-application

    metrics_path: /internal/metrics

    static_configs:
      - targets:
          - app:8000
```

Prometheus retrieves metrics by periodically scraping HTTP endpoints. Its configuration file defines scrape jobs and targets. [Prometheus](https://prometheus.io/docs/prometheus/latest/getting_started/?utm_source=chatgpt.com)

---

# 15. Add Prometheus and Jaeger to Compose

Add these services:

```yaml
services:
  prometheus:
    image: prom/prometheus:v3.13.2

    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --storage.tsdb.retention.time=24h

    ports:
      - "127.0.0.1:9090:9090"

    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus

    networks:
      - backend

    restart: unless-stopped


  jaeger:
    image: cr.jaegertracing.io/jaegertracing/jaeger:2.20.0

    ports:
      - "127.0.0.1:16686:16686"

    expose:
      - "4317"
      - "4318"

    networks:
      - backend

    restart: unless-stopped
```

Add the volume:

```yaml
volumes:
  calculations_data:
  prometheus_data:
```

As of August 4, 2026, Prometheus `3.13.2` is the latest listed LTS release, published July 29, 2026. Jaeger `2.20.0`, published July 20, 2026, is the current documented release and its all-in-one container accepts OTLP and provides the UI on port `16686`. [Prometheus](https://prometheus.io/download/)

Do **not** make application readiness depend on Jaeger or Prometheus:

```text
Telemetry unavailable
    │
    ├── application continues processing MCP requests
    └── telemetry exporter reports delivery failure
```

Observability should normally be best-effort rather than a hard dependency for core request processing.

---

# 16. Test FastMCP Tracing

Create `tests/telemetry/test_tracing.py`:

```python
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastmcp import Client
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


pytestmark = pytest.mark.telemetry


@pytest.fixture(scope="session")
def trace_exporter() -> Iterator[InMemorySpanExporter]:
    exporter = InMemorySpanExporter()

    provider = TracerProvider()
    provider.add_span_processor(
        SimpleSpanProcessor(exporter)
    )

    trace.set_tracer_provider(provider)

    yield exporter

    provider.shutdown()


@pytest.fixture
def clean_trace_exporter(
    trace_exporter: InMemorySpanExporter,
) -> Iterator[InMemorySpanExporter]:
    trace_exporter.clear()

    yield trace_exporter

    trace_exporter.clear()


async def test_add_emits_mcp_tool_span(
    mcp_client: Client,
    clean_trace_exporter: InMemorySpanExporter,
) -> None:
    await mcp_client.call_tool(
        "add",
        {
            "a": 20,
            "b": 22,
        },
    )

    spans = clean_trace_exporter.get_finished_spans()

    tool_spans = [
        span
        for span in spans
        if span.attributes.get("gen_ai.tool.name") == "add"
    ]

    assert tool_spans


async def test_repository_span_is_nested(
    mcp_client: Client,
    clean_trace_exporter: InMemorySpanExporter,
) -> None:
    await mcp_client.call_tool(
        "multiply",
        {
            "a": 6,
            "b": 7,
        },
    )

    spans = clean_trace_exporter.get_finished_spans()

    repository_spans = [
        span
        for span in spans
        if span.name == "calculation_repository.save"
    ]

    assert len(repository_spans) == 1

    repository_span = repository_spans[0]

    assert (
        repository_span.attributes[
            "app.calculation.operation"
        ]
        == "multiply"
    )

    assert repository_span.parent is not None
```

FastMCP documents using the OpenTelemetry in-memory exporter and a simple span processor for deterministic telemetry tests. Native spans use MCP semantic attributes such as `mcp.method.name`, `gen_ai.tool.name`, resource URI, identity, scopes, and error classification. [FastMCP](https://gofastmcp.com/servers/telemetry)

---

# 17. Secure End-to-End Tests

Create `tests/e2e/test_secure_stack.py`:

```python
from __future__ import annotations

import os
from dataclasses import dataclass

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError


pytestmark = pytest.mark.e2e


@dataclass(frozen=True)
class E2ESettings:
    url: str
    certificate: str
    read_token: str
    write_token: str


@pytest.fixture
def e2e_settings() -> E2ESettings:
    required = {
        "url": os.getenv("MCP_E2E_URL"),
        "certificate": os.getenv("MCP_E2E_CA_FILE"),
        "read_token": os.getenv("MCP_E2E_READ_TOKEN"),
        "write_token": os.getenv("MCP_E2E_WRITE_TOKEN"),
    }

    missing = [
        name
        for name, value in required.items()
        if not value
    ]

    if missing:
        pytest.skip(
            "E2E environment is not configured: "
            + ", ".join(missing)
        )

    return E2ESettings(
        url=required["url"],
        certificate=required["certificate"],
        read_token=required["read_token"],
        write_token=required["write_token"],
    )


async def test_missing_token_is_rejected(
    e2e_settings: E2ESettings,
) -> None:
    with pytest.raises(Exception):
        async with Client(
            e2e_settings.url,
            verify=e2e_settings.certificate,
        ) as client:
            await client.list_tools()


async def test_reader_cannot_discover_write_tools(
    e2e_settings: E2ESettings,
) -> None:
    async with Client(
        e2e_settings.url,
        auth=e2e_settings.read_token,
        verify=e2e_settings.certificate,
    ) as client:
        tools = await client.list_tools()

        assert {
            tool.name
            for tool in tools
        }.isdisjoint(
            {
                "add",
                "multiply",
            }
        )

        prompts = await client.list_prompts()

        assert {
            prompt.name
            for prompt in prompts
        } == {
            "explain_arithmetic",
        }


async def test_reader_direct_write_is_denied(
    e2e_settings: E2ESettings,
) -> None:
    async with Client(
        e2e_settings.url,
        auth=e2e_settings.read_token,
        verify=e2e_settings.certificate,
    ) as client:
        with pytest.raises(ToolError):
            await client.call_tool(
                "add",
                {
                    "a": 20,
                    "b": 22,
                },
            )


async def test_writer_can_calculate(
    e2e_settings: E2ESettings,
) -> None:
    async with Client(
        e2e_settings.url,
        auth=e2e_settings.write_token,
        verify=e2e_settings.certificate,
    ) as client:
        result = await client.call_tool(
            "add",
            {
                "a": 20,
                "b": 22,
            },
        )

        assert result.data["result"] == 42
```

The broad exception in the missing-token test is deliberate because authentication failure can surface through different transport exception classes as protocol libraries evolve. Other tests should assert precise application exceptions.

---

# 18. Run the Test Pyramid

## Fast tests

```bash
uv run pytest \
  -m "not integration and not telemetry and not e2e"
```

## Unit and integration

```bash
uv run pytest \
  -m "not e2e"
```

## Individual layer

```bash
uv run pytest tests/protocol -q
```

```bash
uv run pytest tests/integration -q
```

```bash
uv run pytest tests/telemetry -q
```

## Full local suite except Docker

```bash
uv run pytest -m "not e2e"
```

---

# 19. Run Docker End-to-End Tests

Rebuild and start:

```bash
docker compose up \
  --detach \
  --build
```

Export test configuration:

```bash
export MCP_E2E_URL="https://localhost:8443/mcp"

export MCP_E2E_CA_FILE="$PWD/secrets/localhost.crt"

export MCP_E2E_READ_TOKEN="$(
  cat secrets/mcp_read_token.txt
)"

export MCP_E2E_WRITE_TOKEN="$(
  cat secrets/mcp_write_token.txt
)"
```

Run:

```bash
uv run pytest \
  -m e2e \
  -v
```

Unset credentials afterward:

```bash
unset MCP_E2E_READ_TOKEN
unset MCP_E2E_WRITE_TOKEN
```

Do not print the token environment variables in CI logs.

---

# 20. Explore Metrics

Open Prometheus locally:

```text
http://localhost:9090
```

Generate several MCP calls, then query:

## Request rate

```promql
sum(
  rate(
    mcp_http_requests_total{
      endpoint="mcp"
    }[5m]
  )
)
```

## Server-error ratio

```promql
sum(
  rate(
    mcp_http_requests_total{
      endpoint="mcp",
      status_class="5xx"
    }[5m]
  )
)
/
sum(
  rate(
    mcp_http_requests_total{
      endpoint="mcp"
    }[5m]
  )
)
```

## 95th-percentile latency

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(
      mcp_http_request_duration_seconds_bucket{
        endpoint="mcp"
      }[5m]
    )
  )
)
```

## Requests currently executing

```promql
sum(
  mcp_http_requests_in_progress{
    endpoint="mcp"
  }
)
```

These form the **RED signals**:

```text
Rate
Errors
Duration
```

---

# 21. Explore Traces

Open Jaeger:

```text
http://localhost:16686
```

Choose:

```text
Service:
mcp-first-principles
```

Search for a tool call.

Expected shape:

```text
HTTP POST /mcp
└── tools/call add
    └── calculation_repository.save
```

A resource operation should resemble:

```text
HTTP POST /mcp
└── resources/read
    └── calculation_repository.list_recent
```

FastMCP’s server spans include tool and prompt names, resource URIs, protocol version, authenticated client identity, scopes, and standardized error classification. [FastMCP](https://gofastmcp.com/servers/telemetry)

---

# 22. Logs, Metrics, and Traces Answer Different Questions

## Logs

Answer:

> “What specifically happened?”

Example:

```json
{
  "level": "ERROR",
  "request_id": "...",
  "trace_id": "...",
  "message": "http_request_failed"
}
```

## Metrics

Answer:

> “How often is this happening, and is it getting worse?”

Example:

```text
5xx ratio increased from 0.1% to 4%
```

## Traces

Answer:

> “Where did this individual request spend its time?”

Example:

```text
Total:       450 ms
MCP dispatch: 10 ms
SQLite save: 420 ms
Other:        20 ms
```

Professional wording:

> “Logs provide discrete evidence, metrics reveal aggregate behavior, and traces explain causal latency across an individual operation.”

---

# 23. Service-Level Indicators

Useful initial **SLIs**:

| SLI | Measurement |
|---|---|
| Availability | Successful MCP requests / total MCP requests |
| Error rate | Failed MCP requests / total MCP requests |
| Latency | Request-duration percentiles |
| Saturation | In-progress requests and database contention |
| Readiness | Percentage of successful readiness probes |

Do not create an SLO such as:

```text
99.99% availability
```

without:

- Traffic history
- Failure data
- User expectations
- Recovery capability
- Operational staffing
- Dependency reliability

An unsupported SLO is marketing, not engineering.

---

# 24. What Each Test Layer Should Own

| Layer | Verify | Do not verify |
|---|---|---|
| Unit | Business rules | HTTP or SQL |
| Repository integration | SQL and persistence | MCP discovery |
| MCP contract | Schemas, dispatch, errors | TLS certificates |
| ASGI integration | Lifespan and health | Nginx configuration |
| Telemetry | Required spans and attributes | Backend UI rendering |
| End-to-end | TLS, proxy, auth, Docker wiring | Every arithmetic edge case |

A common bad plan is to test every business-rule combination through Docker. That creates a slow and fragile test suite while adding little confidence.

Professional wording:

> “Push exhaustive input coverage downward and reserve end-to-end tests for cross-component wiring.”

---

# 25. Failure Experiments

## Break a unit rule

Change:

```python
return a * b
```

to:

```python
return a + b
```

Expected:

```text
Unit tests fail immediately.
No Docker build required.
```

---

## Break SQL column mapping

Swap:

```python
a=row["operand_a"],
b=row["operand_b"],
```

Expected:

```text
Repository integration test fails.
Service unit tests remain successful.
```

---

## Rename an MCP tool

Change:

```python
async def add(...)
```

to:

```python
async def sum_numbers(...)
```

Expected:

```text
MCP discovery and contract tests fail.
Service tests remain successful.
```

---

## Remove scope authorization

Remove:

```python
auth=require_scopes("calc:write")
```

Expected:

```text
In-memory protocol tests may still pass.
Secure end-to-end authorization tests fail.
```

That proves why authentication needs its own test layer.

---

## Stop Jaeger

```bash
docker compose stop jaeger
```

Expected:

```text
MCP requests continue working.
Trace export reports delivery errors.
```

If the MCP service stops handling requests because Jaeger is unavailable, observability has incorrectly become a critical-path dependency.

---

## Stop Prometheus

```bash
docker compose stop prometheus
```

Expected:

```text
Application metrics endpoint remains available.
No metrics are being collected or stored.
MCP operations continue working.
```

---

# Professional Vocabulary

| Term | Meaning |
|---|---|
| **Test pyramid** | Many small tests beneath fewer broad tests |
| **Unit test** | Isolated test of one behavior or component |
| **Integration test** | Test involving a real adapter or subsystem |
| **Contract test** | Test of an externally visible interface |
| **End-to-end test** | Test spanning the deployed system |
| **Smoke test** | Small test proving basic deployment usability |
| **Fixture** | Reusable test setup and teardown |
| **Parameterized test** | One test executed with several inputs |
| **Test double** | Replacement used instead of a real dependency |
| **Deterministic test** | Test with controlled and repeatable behavior |
| **Test isolation** | One test cannot influence another |
| **Telemetry** | Operational signals emitted by a system |
| **Metric** | Numeric time-series measurement |
| **Counter** | Monotonically increasing metric |
| **Gauge** | Metric that can increase or decrease |
| **Histogram** | Bucketed distribution of observations |
| **Cardinality** | Number of distinct metric-label combinations |
| **Trace** | Complete path of a distributed operation |
| **Span** | Timed unit of work inside a trace |
| **Trace context** | Metadata connecting spans across boundaries |
| **Sampling** | Decision about which traces to retain |
| **Exporter** | Component sending telemetry to a backend |
| **OTLP** | OpenTelemetry Protocol |
| **SLI** | Quantitative service behavior measurement |
| **SLO** | Reliability target for an SLI |
| **RED method** | Rate, errors, and duration |
| **Critical path** | Operations that determine request completion time |

Professional summary:

> “I established a layered pytest suite with isolated domain tests, real SQLite integration tests, in-memory MCP contract tests, telemetry assertions, and authenticated Docker end-to-end coverage. The application now exposes bounded-cardinality Prometheus metrics and exports native FastMCP plus custom repository spans through OpenTelemetry to Jaeger, with trace identifiers correlated into structured logs.”

# Completion Check

```text
[ ] pytest and pytest-asyncio are development dependencies
[ ] Async tests run through asyncio_mode=auto
[ ] Unit tests avoid SQLite and MCP
[ ] Repository tests use temporary SQLite databases
[ ] MCP tests use in-memory transport
[ ] Authorization is tested through the real HTTP deployment
[ ] Test credentials never appear in source control
[ ] Metrics use a per-application CollectorRegistry
[ ] Metric labels have bounded cardinality
[ ] /internal/metrics is not exposed through Nginx
[ ] Prometheus scrapes the application over the backend network
[ ] FastMCP native tracing is enabled
[ ] Repository operations create child spans
[ ] Structured logs include trace and span IDs
[ ] Jaeger receives traces through OTLP
[ ] Telemetry backend failure does not stop MCP traffic
[ ] Docker end-to-end tests remain few and focused
```

## Next increment

The next increment replaces SQLite with PostgreSQL and introduces schema migrations and connection pooling:

```text
Nginx
    │
    ▼
Several application replicas
    │
    ├── bounded connection pools
    ├── transactional repository
    └── retry classification
            │
            ▼
        PostgreSQL
        ├── migrations
        ├── concurrent writes
        └── durable shared state
```