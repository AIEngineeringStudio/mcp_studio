| Stack                 | Server import                            | How to launch               |
|-----------------------|------------------------------------------|-----------------------------|
| New FastMCP           | `from fastmcp import FastMCP`            | `python my_stdio_server.py` |
| Older MCP SDK FastMCP | `from mcp.server.fastmcp import FastMCP` | older `mcp run ...` flow    |

New FastMCP: args=["run", "python", str(SERVER)]

```    
server_params = StdioServerParameters(
    command="uv",
    args=["run", "python", str(SERVER)],  # start server as subprocess
    env={"PYTHONUNBUFFERED": "1"},        # start server as subprocess
)
```

Older MCP SDK FastMCP: args=["run", "mcp", "run", str(SERVER)]

```    
server_params = StdioServerParameters(
    command="uv",
    args=["run", "mcp", "run", str(SERVER)],  # start server as subprocess
    env={"PYTHONUNBUFFERED": "1"},            # start server as subprocess
)
```

### asyncio vs anyio

| Part                        | Reason                   |
|-----------------------------|--------------------------|
| `anyio.run(main)`           | correct AnyIO usage      |
| `with anyio.fail_after(30)` | standard timeout pattern |

asyncio version:

```
await asyncio.wait_for(session.initialize(), timeout=30)
```

anyio version:

```
with anyio.fail_after(30):
    await session.initialize()
```

---

# Use `uv` in Docker

1. Option 1: `requirements.txt`
2. Option 2: `pyproject.toml`

Why:

- `uv` can replace `pip install -r requirements.txt`.
- `uv` works well in containers and supports Docker-specific patterns like
  copying the `uv` binary from Astral’s image.

**Example Docker file with requirements.txt**

```
FROM python:3.14.3-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Alternative: install uv with pip
# RUN pip install --no-cache-dir uv

COPY requirements.txt ./

# Install into the system Python inside the container
RUN uv pip install --system --no-cache -r requirements.txt

COPY app ./app

CMD ["python", "-m", "app.client"]
```

uv is strongest when you use:

- `pyproject.toml`
- `uv.lock`

Then Docker often uses `uv sync`. Astral’s Docker guide recommends this
project-based workflow and shows layer optimization patterns such as installing
dependencies separately from project code.

**Example Docker file - full uv style**

```
FROM python:3.14.3-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.8.13 /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app

CMD ["uv", "run", "python", "-m", "app.client"]
```

**Notes:**

- `--frozen` uses the lock file exactly.
- This is better for reproducible builds.
- This is the modern uv workflow.

**Comparison**

| Approach          | Dependency file          | Install command                               | Best for                          |
|-------------------|--------------------------|-----------------------------------------------|-----------------------------------|
| pip style with uv | requirements.txt         | `uv pip install --system -r requirements.txt` | Easy migration                    |
| full uv project   | pyproject.toml + uv.lock | `uv sync --frozen`                            | New projects, reproducible builds |

When you run: `uv sync --frozen --no-dev` you do NOT need `--system`.

**Why**

`uv` has two different behaviors:

| Command        | Default target             | Need `--system`? |
|----------------|----------------------------|------------------|
| uv pip install | system Python              | YES              |
| uv sync        | project virtualenv (.venv) | NO               |

Explanation
-----------

`uv sync` installs dependencies into a **project virtual environment**.

Default location:

    /app/.venv

So the flow is:

1. Read `pyproject.toml`
2. Read `uv.lock`
3. Create `.venv`
4. Install packages into `.venv`

**Diagram**

```
    Container Python
          │
          │
          ├── /usr/local/lib/python3.x   (system Python)
          │
          └── /app
                │
                ├── pyproject.toml
                ├── uv.lock
                └── .venv
                      │
                      └── site-packages (dependencies)
```

Because `uv sync` installs into `.venv`, there is **no need for `--system`**.




```
streamable-http-mcp/
├── README.md
├── app/
│   ├── bridge/
│   │   ├── bridge.py
│   │   ├── trace_bus.py
│   │   └── trace_models.py
│   ├── config.py
│   ├── connection.py
│   └── repositories/
│       └── user_repo.py
├── db/
│└── init/
│    └── 001_seed.sql
├── docker-compose.yml
└── server/
    ├── Dockerfile
    ├── ENV_SETUP.md
    ├── app/
    │   ├── __init__.py
    │   └── server.py
    └── pyproject.toml
```