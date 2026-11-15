# MCP Tutorial — Chunk 3 of 8

# MCP Tutorial — Chunk 3 of 8
## CHUNKS GENERATED: [3 / 8]
## ACTIVE CHUNK: [3 / 8]
## SECTIONS IN THIS CHUNK: [§05, §06]

---

## §05. BASIC EXAMPLE

Build a minimal MCP server that exposes one tool: `get_weather`.
The AI agent calls it. We verify the round-trip.


![mcp_chunk3_architecture.svg](../../assets/chunks/mcp_chunk3.png)

---

### Project Structure

```
mcp-basic/
├── docker-compose.yml
├── nginx/
│   └── nginx.conf
├── server/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── src/
│       ├── main.py          # FastAPI + MCP server entry
│       ├── tools/
│       │   └── weather.py   # Tool implementation
│       └── logging_cfg.py   # Structured logging setup
└── agent/
    ├── Dockerfile
    ├── pyproject.toml
    └── src/
        └── agent.py         # OpenAI Agent SDK client
```

---

### Step 1 — Setup Dependencies

**server/pyproject.toml**
```toml
[project]
name = "mcp-server"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
  "fastapi>=0.115",        # HTTP framework
  "uvicorn>=0.29",         # ASGI server
  "mcp[cli]>=1.6",         # MCP SDK (server side)
  "litellm>=1.40",         # LLM abstraction layer
  "structlog>=24.1",       # Structured logging
  "python-dotenv>=1.0",    # Env var loading
]
```

**agent/pyproject.toml**
```toml
[project]
name = "mcp-agent"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
  "openai-agents>=0.0.12",  # OpenAI Agent SDK
  "mcp[cli]>=1.6",          # MCP SDK (client side)
  "structlog>=24.1",
  "python-dotenv>=1.0",
]
```

---

### Step 2 — Structured Logging

**server/src/logging_cfg.py**
```python
import structlog

def configure_logging() -> None:
    """Configure structlog for JSON output."""
    structlog.configure(
        processors=[
            # Add log level to every event
            structlog.stdlib.add_log_level,
            # Add ISO timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Render as JSON — machine-readable
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

# Module-level logger — import this everywhere
log = structlog.get_logger()
```

---

### Step 3 — Tool Implementation

**server/src/tools/weather.py**
```python
from mcp.server.fastmcp import FastMCP

# FastMCP is the high-level MCP server builder
mcp = FastMCP(name="weather-server")


@mcp.tool()
def get_weather(city: str) -> dict:
    """
    Return mock weather data for a city.

    Args:
        city: Name of the city to query.

    Returns:
        dict with temperature, condition, city.
    """
    # Hardcoded mock data — no real API needed
    mock_data = {
        "london":   {"temp_c": 12, "condition": "Cloudy"},
        "tokyo":    {"temp_c": 24, "condition": "Sunny"},
        "new york": {"temp_c": 18, "condition": "Rainy"},
    }

    key = city.lower()

    # Return data if city found, else return error dict
    if key in mock_data:
        return {"city": city, **mock_data[key]}
    else:
        return {"city": city, "error": "City not found"}
```

---

### Step 4 — FastAPI Entry Point

**server/src/main.py**
```python
import uvicorn
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from logging_cfg import configure_logging, log
from tools.weather import mcp  # Import the MCP instance

# Initialize structured logging first
configure_logging()

# FastAPI app — acts as the HTTP gateway
app = FastAPI(title="MCP Weather Server")


@app.get("/health")
async def health() -> dict:
    """Health check endpoint for Docker/Nginx."""
    log.info("health_check", status="ok")
    return {"status": "ok"}


# Mount the MCP server at /mcp using SSE transport
# SSE = Server-Sent Events — keeps connection open
# for streaming tool responses back to the client
app.mount("/mcp", mcp.sse_app())

if __name__ == "__main__":
    log.info("server_starting", host="0.0.0.0", port=8000)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,       # Disable in production
        log_level="warning" # Structlog handles logging
    )
```

---

### Step 5 — Agent Client

**agent/src/agent.py**
```python
import asyncio
from agents import Agent, Runner
from agents.mcp import MCPServerSse
from dotenv import load_dotenv
import structlog

# Load OPENAI_API_KEY from .env file
load_dotenv()

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
)
log = structlog.get_logger()


async def main() -> None:
    # MCPServerSse connects to our server over SSE
    # url points to the /mcp endpoint via Nginx
    async with MCPServerSse(
        name="weather-server",
        params={"url": "http://nginx/mcp/sse"},
    ) as mcp_server:

        log.info("mcp_connected", server="weather-server")

        # Agent is told it can call tools from mcp_server
        agent = Agent(
            name="WeatherAgent",
            instructions=(
                "You are a helpful assistant. "
                "Use get_weather to answer weather questions."
            ),
            mcp_servers=[mcp_server],
        )

        # Run the agent with a user prompt
        result = await Runner.run(
            agent,
            input="What is the weather in Tokyo?",
        )

        # Print the final text response
        log.info("agent_response", output=result.final_output)
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
```

---

### Step 6 — Dockerfile (Server)

**server/Dockerfile**
```dockerfile
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Install uv — fast Python package manager
RUN pip install uv

# Copy dependency manifest first (layer caching)
COPY pyproject.toml .

# Install all dependencies with uv
RUN uv pip install --system -e .

# Copy application source code
COPY src/ ./src/

# Run uvicorn pointing to the main:app object
CMD ["uvicorn", "src.main:app",
     "--host", "0.0.0.0",
     "--port", "8000"]
```

---

### Step 7 — Nginx Config

**nginx/nginx.conf**
```nginx
events {}

http {
  upstream mcp_server {
    # Docker service name resolves to container IP
    server mcp-server:8000;
  }

  server {
    listen 80;

    # Forward all /mcp/* requests to the MCP server
    location /mcp/ {
      proxy_pass         http://mcp_server;
      # Required for SSE — disables response buffering
      proxy_buffering    off;
      proxy_cache        off;
      # Keep connection alive for SSE streaming
      proxy_set_header   Connection '';
      proxy_http_version 1.1;
      chunked_transfer_encoding on;
    }

    # Health check passthrough
    location /health {
      proxy_pass http://mcp_server;
    }
  }
}
```

---

### Step 8 — Docker Compose

**docker-compose.yml**
```yaml
version: "3.9"

services:
  mcp-server:
    build: ./server
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    networks:
      - mcp-net

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"             # Expose port 80 to host
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - mcp-server
    networks:
      - mcp-net

  agent:
    build: ./agent
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - nginx
    networks:
      - mcp-net

networks:
  mcp-net:
    driver: bridge   # All containers share this network
```

---

### Step 9 — Run and Verify

```bash
# 1. Set your API key
export OPENAI_API_KEY=sk-...

# 2. Build and start all containers
docker compose up --build

# 3. Verify server health
curl http://localhost/health
# Expected: {"status":"ok"}

# 4. Run the agent (in a second terminal)
docker compose run agent python src/agent.py
```

**Expected Output:**
```
{"event": "mcp_connected", "server": "weather-server", ...}
{"event": "agent_response",
 "output": "The weather in Tokyo is 24°C and Sunny.", ...}

The weather in Tokyo is 24°C and Sunny.
```

---

### Flow Diagram — §05

```
┌──────────┐   HTTP/SSE    ┌─────────┐  proxy  ┌────────────┐
│  Agent   │ ────────────► │  Nginx  │ ───────► │ MCP Server │
│(SDK)     │               │ :80     │          │ :8000      │
│          │ ◄──────────── │         │ ◄─────── │            │
└──────────┘  tool result  └─────────┘          └────────────┘

Steps:
1. Agent connects to Nginx /mcp/sse
2. Nginx proxies SSE stream to MCP Server
3. Agent sends tool call: get_weather("Tokyo")
4. MCP Server executes get_weather()
5. Result streams back through Nginx to Agent
6. Agent formats result → final_output
```

---

## §06. INTERMEDIATE LEVEL

Add: multi-tool server, PostgreSQL tool, structured error
handling, and a real agent loop.

---

### What Changes at Intermediate Level

```
Basic                     Intermediate
──────────────────────    ──────────────────────────────
1 tool                →   Multiple tools
Mock data             →   Real PostgreSQL queries
No error handling     →   Typed errors + fallbacks
Single turn agent     →   Multi-turn agent loop
No DB                 →   Ports & Adapters DB layer
```

---

### Updated Project Structure

```
mcp-intermediate/
├── docker-compose.yml
├── nginx/nginx.conf
├── postgres/
│   └── init.sql             # DB seed data
├── server/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── src/
│       ├── main.py
│       ├── logging_cfg.py
│       ├── domain/
│       │   └── models.py    # Pure domain types
│       ├── ports/
│       │   └── db_port.py   # Abstract DB interface
│       ├── adapters/
│       │   └── postgres.py  # PostgreSQL adapter
│       └── tools/
│           ├── weather.py
│           └── product.py   # New tool: DB query
└── agent/
    └── src/agent.py
```

---

### Ports & Adapters Pattern (DB Layer)

🔑 **Port** — abstract interface (what the app expects)
🔑 **Adapter** — concrete implementation (how it connects)

```
┌─────────────────────────────────────────────┐
│               MCP Tool Layer                │
│  tool calls port.get_product(id)            │
└──────────────────┬──────────────────────────┘
                   │ depends on abstraction
┌──────────────────▼──────────────────────────┐
│               Port (Interface)              │
│  class ProductPort(ABC):                    │
│      def get_product(id) -> Product         │
└──────────────────┬──────────────────────────┘
                   │ implemented by
┌──────────────────▼──────────────────────────┐
│            PostgreSQL Adapter               │
│  class PostgresAdapter(ProductPort):        │
│      def get_product(id) -> Product         │
└─────────────────────────────────────────────┘
```

---

### Step 1 — Domain Models

**server/src/domain/models.py**
```python
from dataclasses import dataclass
from typing import Optional


@dataclass
class Product:
    """
    Pure domain object — no DB or framework imports.
    Represents a product record from the database.
    """
    id: int
    name: str
    price_usd: float
    stock: int


@dataclass
class ToolError:
    """
    Structured error returned when a tool fails.
    Avoids raw exceptions leaking to the LLM.
    """
    code: str          # Machine-readable error code
    message: str       # Human-readable description
    tool: str          # Which tool raised the error
```

---

### Step 2 — Port (Abstract Interface)

**server/src/ports/db_port.py**
```python
from abc import ABC, abstractmethod
from typing import Optional
from domain.models import Product


class ProductRepositoryPort(ABC):
    """
    Port defines WHAT operations are needed.
    The tool layer depends ONLY on this interface.
    Swapping PostgreSQL for another DB = zero tool
    code changes.
    """

    @abstractmethod
    async def get_by_id(
        self, product_id: int
    ) -> Optional[Product]:
        """Fetch one product by primary key."""
        ...

    @abstractmethod
    async def list_all(self) -> list[Product]:
        """Return all products in the catalogue."""
        ...
```

---

### Step 3 — PostgreSQL Adapter

**server/src/adapters/postgres.py**
```python
import asyncpg               # Async PostgreSQL driver
from typing import Optional
from domain.models import Product
from ports.db_port import ProductRepositoryPort
from logging_cfg import log


class PostgresProductAdapter(ProductRepositoryPort):
    """
    Adapter implements HOW we talk to PostgreSQL.
    Only this file knows about asyncpg or SQL.
    """

    def __init__(self, dsn: str) -> None:
        # DSN = Data Source Name
        # e.g. postgresql://user:pass@host/db
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Create a connection pool on startup."""
        self._pool = await asyncpg.create_pool(
            self._dsn,
            min_size=2,   # Keep 2 connections warm
            max_size=10,  # Max 10 concurrent queries
        )
        log.info("db_pool_created", dsn=self._dsn)

    async def disconnect(self) -> None:
        """Release all connections on shutdown."""
        if self._pool:
            await self._pool.close()

    async def get_by_id(
        self, product_id: int
    ) -> Optional[Product]:
        """Run SELECT query for one product."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, price_usd, stock "
                "FROM products WHERE id = $1",
                product_id,
            )
        if row is None:
            return None
        # Map raw DB row → clean domain object
        return Product(
            id=row["id"],
            name=row["name"],
            price_usd=float(row["price_usd"]),
            stock=row["stock"],
        )

    async def list_all(self) -> list[Product]:
        """Fetch all rows from products table."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, name, price_usd, stock "
                "FROM products ORDER BY id"
            )
        return [
            Product(
                id=r["id"],
                name=r["name"],
                price_usd=float(r["price_usd"]),
                stock=r["stock"],
            )
            for r in rows
        ]
```

---

### Step 4 — Product Tool

**server/src/tools/product.py**
```python
from mcp.server.fastmcp import FastMCP
from domain.models import Product, ToolError
from ports.db_port import ProductRepositoryPort
from logging_cfg import log

mcp = FastMCP(name="product-server")

# Injected at startup — tool does not know the DB type
_repo: ProductRepositoryPort | None = None


def set_repository(repo: ProductRepositoryPort) -> None:
    """Inject the DB adapter at runtime."""
    global _repo
    _repo = repo


@mcp.tool()
async def get_product(product_id: int) -> dict:
    """
    Fetch a product by ID from the catalogue.

    Args:
        product_id: Integer primary key.

    Returns:
        Product dict or error dict.
    """
    if _repo is None:
        # Repository not injected — config error
        return ToolError(
            code="NOT_INITIALIZED",
            message="Repository not set",
            tool="get_product",
        ).__dict__

    log.info("tool_called", tool="get_product",
             product_id=product_id)

    product = await _repo.get_by_id(product_id)

    if product is None:
        return ToolError(
            code="NOT_FOUND",
            message=f"Product {product_id} not found",
            tool="get_product",
        ).__dict__

    # Return domain object as plain dict for MCP
    return product.__dict__


@mcp.tool()
async def list_products() -> list[dict]:
    """Return all products in the catalogue."""
    if _repo is None:
        return []

    products = await _repo.list_all()
    log.info("tool_called", tool="list_products",
             count=len(products))
    return [p.__dict__ for p in products]
```

---

### Step 5 — Updated main.py

**server/src/main.py**
```python
import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from logging_cfg import configure_logging, log
from tools.weather import mcp as weather_mcp
from tools.product import mcp as product_mcp, set_repository
from adapters.postgres import PostgresProductAdapter

configure_logging()

# Read DSN from environment variable
DB_DSN = os.environ["DATABASE_URL"]

# Adapter instance — only created once
db_adapter = PostgresProductAdapter(dsn=DB_DSN)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan manages startup and shutdown side effects.
    Replaces deprecated @app.on_event handlers.
    """
    # STARTUP: connect DB, inject into tool
    await db_adapter.connect()
    set_repository(db_adapter)
    log.info("startup_complete")
    yield
    # SHUTDOWN: close DB pool
    await db_adapter.disconnect()
    log.info("shutdown_complete")


app = FastAPI(title="MCP Intermediate", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# Mount both MCP servers under separate paths
app.mount("/mcp/weather", weather_mcp.sse_app())
app.mount("/mcp/product", product_mcp.sse_app())
```

---

### Step 6 — DB Seed

**postgres/init.sql**
```sql
CREATE TABLE IF NOT EXISTS products (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    price_usd  NUMERIC(10, 2) NOT NULL,
    stock      INTEGER NOT NULL
);

INSERT INTO products (name, price_usd, stock) VALUES
    ('Laptop Pro 15',  1299.99, 42),
    ('Wireless Mouse',   29.99, 200),
    ('USB-C Hub',        49.99, 85);
```

---

### Step 7 — Updated Agent

**agent/src/agent.py**
```python
import asyncio
from agents import Agent, Runner
from agents.mcp import MCPServerSse
from dotenv import load_dotenv
import structlog

load_dotenv()

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
)
log = structlog.get_logger()


async def main() -> None:
    # Connect to both MCP servers
    async with (
        MCPServerSse(
            name="weather",
            params={"url": "http://nginx/mcp/weather/sse"},
        ) as weather_server,
        MCPServerSse(
            name="product",
            params={"url": "http://nginx/mcp/product/sse"},
        ) as product_server,
    ):
        agent = Agent(
            name="ShopAssistant",
            instructions=(
                "Help users with weather and product queries. "
                "Use get_weather for weather questions. "
                "Use get_product or list_products for "
                "catalogue questions."
            ),
            mcp_servers=[weather_server, product_server],
        )

        # Multi-turn loop
        queries = [
            "List all available products.",
            "What is the price of product 1?",
            "What is the weather in London?",
        ]

        for query in queries:
            log.info("agent_query", input=query)
            result = await Runner.run(agent, input=query)
            log.info("agent_response", output=result.final_output)
            print(f"\nQ: {query}")
            print(f"A: {result.final_output}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

### Step 8 — Updated Docker Compose

**docker-compose.yml**
```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: mcp
      POSTGRES_PASSWORD: mcp
      POSTGRES_DB: mcpdb
    volumes:
      # Run init.sql automatically on first start
      - ./postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - mcp-net

  mcp-server:
    build: ./server
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=postgresql://mcp:mcp@postgres/mcpdb
    depends_on:
      - postgres
    networks:
      - mcp-net

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - mcp-server
    networks:
      - mcp-net

  agent:
    build: ./agent
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - nginx
    networks:
      - mcp-net

networks:
  mcp-net:
    driver: bridge
```

---

### Expected Output

```
Q: List all available products.
A: Here are the available products:
   1. Laptop Pro 15  — $1,299.99 (42 in stock)
   2. Wireless Mouse — $29.99   (200 in stock)
   3. USB-C Hub      — $49.99   (85 in stock)

Q: What is the price of product 1?
A: Product 1 is the Laptop Pro 15, priced at $1,299.99.

Q: What is the weather in London?
A: The weather in London is 12°C and Cloudy.
```

---

### Flow Diagram — §06

```
┌─────────┐     SSE      ┌─────────┐    ┌──────────────────┐
│  Agent  │ ──────────►  │  Nginx  │ ─► │  MCP Server      │
│         │              │         │    │  ┌─────────────┐  │
│ 2 MCP   │              │ /weather│    │  │ weather tool│  │
│ servers │              │ /product│    │  ├─────────────┤  │
│         │ ◄──────────  │         │ ◄─ │  │ product tool│  │
└─────────┘  tool result └─────────┘    │  └──────┬──────┘  │
                                        │         │         │
                                        │  ┌──────▼──────┐  │
                                        │  │  Port       │  │
                                        │  │  (abstract) │  │
                                        │  └──────┬──────┘  │
                                        │         │         │
                                        │  ┌──────▼──────┐  │
                                        │  │  Postgres   │  │
                                        │  │  Adapter    │  │
                                        └──┴──────┬──────┴──┘
                                                  │
                                         ┌────────▼────────┐
                                         │   PostgreSQL    │
                                         │   :5432         │
                                         └─────────────────┘
```

---

### Edge Cases

| Scenario | Behavior | Why |
|---|---|---|
| DB down at startup | `connect()` raises — container exits | asyncpg raises on failed pool creation |
| Product ID not found | Returns `ToolError(NOT_FOUND)` dict | Tool never raises raw exceptions |
| City not in mock data | Returns `{"error": "City not found"}` | LLM receives clean dict, not exception |
| Nginx down | Agent raises `ConnectionRefusedError` | SSE handshake fails before any tool call |
| DB pool exhausted | Query waits up to pool timeout | asyncpg queues requests beyond `max_size` |

---

### Key Limitations

1. **No auth on MCP endpoints** — any caller can invoke tools.
   Fix in §07 (Advanced).

2. **Mock weather data** — no real API integration yet.
   Replace `mock_data` dict with `httpx` call to a weather API.

3. **Single MCP server process** — no horizontal scaling.
   Fix in §07 with load balancing + stateless design.

---

### 🔑 Jargon Summary — §05 & §06

| Term | Definition |
|---|---|
| **FastMCP** | High-level MCP server builder from the MCP SDK |
| **SSE** | Server-Sent Events — HTTP streaming for tool responses |
| **MCPServerSse** | Agent SDK class that connects to an SSE MCP server |
| **Port** | Abstract interface defining DB operations |
| **Adapter** | Concrete class implementing a Port for one DB type |
| **DSN** | Data Source Name — connection string for a database |
| **asyncpg** | Async Python driver for PostgreSQL |
| **Connection Pool** | Pre-created set of DB connections for reuse |
| **Lifespan** | FastAPI context manager for startup/shutdown logic |
| **ToolError** | Typed dict returned on tool failure (no raw exceptions) |
| **Dependency Injection** | Passing adapters into tools at runtime, not hardcoded |