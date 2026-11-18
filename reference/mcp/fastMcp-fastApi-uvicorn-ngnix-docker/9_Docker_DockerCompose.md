# Increment 9 — Docker and Docker Compose

## Goal

Package the application and reverse proxy into separate containers:

```text
Host machine
    │
    │ 127.0.0.1:8080
    ▼
┌──────────────────────────────┐
│ Nginx container              │
│                              │
│ Published port: 8080         │
│ Backend IP: 172.28.0.10      │
└──────────────┬───────────────┘
               │ app:8000
               │ private Docker network
               ▼
┌──────────────────────────────┐
│ Application container        │
│                              │
│ Uvicorn :8000                │
│ FastAPI + FastMCP            │
│ No published host port       │
└──────────────┬───────────────┘
               │
               ▼
       Docker named volume
       calculations.db
```

Docker Compose provides internal DNS, so Nginx can resolve the application by its service name, `app`, rather than by a manually discovered container IP. Compose networks can also be marked `internal`, removing their external gateway. [Docker Documentation](https://docs.docker.com/compose/how-tos/networking/?utm_source=chatgpt.com)

---

## 1. Important Container Networking Correction

Outside Docker, we ran Uvicorn with:

```bash
--host 127.0.0.1
```

Inside the application container, that would be wrong:

```text
Nginx container
    │
    └── cannot reach 127.0.0.1 in application container
```

Every container has its own network namespace:

```text
Nginx 127.0.0.1
└── means Nginx container itself

Application 127.0.0.1
└── means application container itself
```

Uvicorn must therefore bind to:

```bash
--host 0.0.0.0
```

inside its container.

Security now comes from:

```text
Application port listens inside container
        │
        ├── no host port published
        ├── private backend network only
        └── Nginx is the only attached proxy
```

Professional wording:

> “The process binds to all interfaces within its isolated container namespace, while Docker network policy prevents direct host exposure.”

---

# 2. Final Project Structure

```text
mcp-first-principles/
├── nginx/
│   └── default.conf
├── app.py
├── server.py
├── service.py
├── repository.py
├── models.py
├── errors.py
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── compose.yaml
└── .dockerignore
```

Do not include a top-level Compose `version:` field. Current Compose treats it as obsolete and uses the current Compose Specification. [Docker Documentation](https://docs.docker.com/reference/compose-file/version-and-name/?utm_source=chatgpt.com)

---

# 3. Create `.dockerignore`

```dockerignore
.git
.gitignore

.venv
__pycache__
*.py[cod]

.pytest_cache
.mypy_cache
.ruff_cache

.env
.env.*

data
*.db
*.db-shm
*.db-wal

test_*.py

nginx
compose.yaml
Dockerfile
```

The Docker build context is everything available to `COPY` and related build instructions. Keeping it small improves build caching and reduces the chance of accidentally including local environments, databases, credentials, or repository metadata. [Docker Documentation](https://docs.docker.com/build/cache/optimize/?utm_source=chatgpt.com)

The critical exclusions are:

```text
.venv
└── Host-specific virtual environment

.env
└── Potential secrets

data and *.db
└── Runtime state must not become image content

.git
└── Repository history is unnecessary at runtime
```

---

# 4. Create the Application `Dockerfile`

This example assumes Python 3.13. Change `PYTHON_VERSION` to match the `requires-python` value in your `pyproject.toml`.

```dockerfile
# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.13


# ---------------------------------------------------------------------------
# Builder stage
# ---------------------------------------------------------------------------

FROM python:${PYTHON_VERSION}-slim-trixie AS builder

# Pin uv rather than using a moving "latest" tag.
COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies in a cacheable layer before copying source code.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync \
        --locked \
        --no-dev \
        --no-install-project

# Copy application source after dependency installation.
COPY . /app

# Install the project itself and verify that uv.lock is current.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync \
        --locked \
        --no-dev \
        --no-editable


# ---------------------------------------------------------------------------
# Runtime stage
# ---------------------------------------------------------------------------

FROM python:${PYTHON_VERSION}-slim-trixie AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CALC_DB_PATH=/data/calculations.db

# Run the application as a dedicated non-root account.
RUN groupadd \
        --system \
        --gid 10001 \
        app \
    && useradd \
        --system \
        --uid 10001 \
        --gid app \
        --home-dir /app \
        --shell /usr/sbin/nologin \
        app \
    && mkdir -p /app /data \
    && touch /data/.volume-owner \
    && chown -R app:app /app /data

WORKDIR /app

COPY --from=builder \
    --chown=app:app \
    /app \
    /app

USER app

EXPOSE 8000

HEALTHCHECK \
    --interval=10s \
    --timeout=3s \
    --start-period=10s \
    --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2).read()"]

CMD [
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
    "--log-level", "info"
]
```

Astral’s current Docker guidance recommends pinning uv, separating dependency installation from source copying for better cache reuse, using `uv sync --locked`, excluding development dependencies, and optionally compiling bytecode for faster container startup. The current documented pinned version is `0.12.1`. [Astral Docs](https://docs.astral.sh/uv/guides/integration/docker/?utm_source=chatgpt.com)

---

# 5. Understand the Two Build Stages

## Builder stage

```text
Builder image
├── Python
├── uv
├── dependency cache
├── compilers if later required
├── source code
└── resulting .venv
```

Its job is to produce the runtime artifacts.

## Runtime stage

```text
Runtime image
├── Python
├── source code
├── completed .venv
└── no uv binary required
```

The final image does not inherit the builder’s package cache or build tooling.

```text
Builder stage
    │
    └── COPY /app into runtime
              │
              ▼
          Final image
```

Professional wording:

> “The multi-stage build separates dependency construction from runtime execution, reducing the final image’s toolchain and attack surface.”

---

# 6. Why Dependencies Are Installed Before Source Code

This ordering is deliberate:

```dockerfile
RUN uv sync --no-install-project
COPY . /app
RUN uv sync
```

Docker can reuse an unchanged dependency layer when application source files change but `pyproject.toml` and `uv.lock` do not.

```text
Change service.py
├── dependency layer remains cached
└── application layer is rebuilt

Change uv.lock
├── dependency layer is invalidated
└── dependencies are installed again
```

Docker’s build cache works by reusing matching layers; ordering stable dependency inputs before frequently changing source improves cache effectiveness. [Docker Documentation](https://docs.docker.com/build/cache/optimize/?utm_source=chatgpt.com)

Professional term:

> **Cache-aware layer ordering**

---

# 7. Why the Image Runs as Non-Root

The runtime stage declares:

```dockerfile
USER app
```

This means application-level compromise does not automatically begin with root privileges inside the container.

The user has fixed identifiers:

```text
UID: 10001
GID: 10001
```

Fixed numeric identifiers make filesystem ownership predictable across builds.

The application requires write access only to:

```text
/data
```

It does not need to modify:

```text
/app
/usr
/etc
```

Professional wording:

> “The container follows least privilege by running under a dedicated unprivileged UID with a narrowly scoped writable data path.”

---

# 8. Why `/data/.volume-owner` Exists

The image creates:

```dockerfile
touch /data/.volume-owner
chown -R app:app /data
```

When Docker creates a new empty volume over a container directory containing existing files, it copies that directory’s existing content into the new volume by default. This allows the new named volume to inherit initialized content and ownership from `/data`. [Docker Documentation](https://docs.docker.com/engine/storage/volumes/?utm_source=chatgpt.com)

```text
Image /data
├── owner app:app
└── .volume-owner

First volume mount
        │
        ▼
Docker copies initial content
        │
        ▼
Named volume
├── writable by app
└── calculations.db created later
```

If you previously created the volume using a differently configured image, remove and recreate that development volume before testing ownership:

```bash
docker compose down --volumes
```

That command deletes the database. Use it only when intentional.

---

# 9. Create `nginx/default.conf`

The upstream address changes from:

```nginx
server 127.0.0.1:8000;
```

to:

```nginx
server app:8000;
```

Full configuration:

```nginx
upstream mcp_backend {
    server app:8000;
    keepalive 16;
}

server {
    listen 8080;
    server_name localhost 127.0.0.1;

    client_max_body_size 1m;

    proxy_http_version 1.1;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_set_header Connection "";
    proxy_redirect off;

    # ------------------------------------------------------------------
    # MCP endpoint
    # ------------------------------------------------------------------

    location = /mcp {
        proxy_pass http://mcp_backend;

        proxy_buffering off;
        proxy_request_buffering on;
        proxy_cache off;

        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 3600s;
    }

    # ------------------------------------------------------------------
    # Health endpoints
    # ------------------------------------------------------------------

    location = /health/live {
        proxy_pass http://mcp_backend;

        proxy_connect_timeout 2s;
        proxy_read_timeout 5s;
    }

    location = /health/ready {
        proxy_pass http://mcp_backend;

        proxy_connect_timeout 2s;
        proxy_read_timeout 5s;
    }

    # Default-deny every other application route.
    location / {
        return 404;
    }
}
```

Compose registers service names in its internal DNS, so `app` resolves to the application service on their shared network. No `container_name` or manually discovered address is required. [Docker Documentation](https://docs.docker.com/compose/how-tos/networking/?utm_source=chatgpt.com)

Do not use:

```nginx
server localhost:8000;
```

Inside the Nginx container, `localhost` means Nginx itself.

---

# 10. Create `compose.yaml`

```yaml
name: mcp-first-principles

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        PYTHON_VERSION: "3.13"

    image: mcp-first-principles-app:local

    environment:
      CALC_DB_PATH: /data/calculations.db

    volumes:
      - calculations_data:/data

    expose:
      - "8000"

    networks:
      backend:
        ipv4_address: 172.28.0.20

    init: true
    restart: unless-stopped
    stop_grace_period: 30s

    read_only: true

    tmpfs:
      - /tmp:size=64m,mode=1777

    security_opt:
      - no-new-privileges:true

  nginx:
    image: nginx:1.30.4-alpine3.24

    depends_on:
      app:
        condition: service_healthy
        restart: true

    ports:
      - "127.0.0.1:8080:8080"

    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro

    networks:
      edge:
      backend:
        ipv4_address: 172.28.0.10

    init: true
    restart: unless-stopped
    stop_grace_period: 10s

    read_only: true

    tmpfs:
      - /var/cache/nginx:size=32m
      - /var/run:size=1m
      - /tmp:size=16m

    security_opt:
      - no-new-privileges:true

    healthcheck:
      test:
        - CMD-SHELL
        - >-
          wget -q -O /dev/null
          http://127.0.0.1:8080/health/live
          || exit 1
      interval: 10s
      timeout: 3s
      start_period: 5s
      retries: 3

networks:
  edge:
    driver: bridge

  backend:
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.28.0.0/24

volumes:
  calculations_data:
```

The current official stable Alpine Nginx image is available as `nginx:1.30.4-alpine3.24`; using a concrete tag is more reproducible than using `nginx:latest`. Environments requiring stronger supply-chain reproducibility should pin image digests as well. [Docker Hub](https://hub.docker.com/_/nginx/tags?utm_source=chatgpt.com)

---

# 11. Understand the Two Networks

## `edge`

```text
Host port 8080
    │
    ▼
Nginx
```

Only Nginx joins the edge network.

## `backend`

```text
Nginx
    │
    ▼
Application
```

The backend network is:

```yaml
internal: true
```

Docker defines internal networks as externally isolated networks without the ordinary external gateway. Containers on the network can communicate with one another, but the network itself does not provide normal external routing. [Docker Documentation](https://docs.docker.com/reference/compose-file/networks/?utm_source=chatgpt.com)

The application joins only:

```text
backend
```

Nginx joins:

```text
edge
backend
```

That makes Nginx the network bridge between client traffic and the private application service.

Professional wording:

> “The proxy is dual-homed across edge and backend networks, while the application is single-homed on the isolated backend segment.”

---

# 12. Why the Application Has No `ports`

The application declares:

```yaml
expose:
  - "8000"
```

but does not declare:

```yaml
ports:
  - "8000:8000"
```

The result is:

```text
Nginx container → app:8000       allowed
Host → localhost:8000            unavailable
Host → localhost:8080 → Nginx    allowed
```

This prevents bypassing:

- Nginx route restrictions
- Nginx body-size limits
- Nginx timeout policy
- Nginx access logging
- Future TLS and authentication controls

Professional wording:

> “The upstream port is container-network reachable but not host-published.”

---

# 13. Why Uvicorn Trusts `172.28.0.10`

The Uvicorn command contains:

```bash
--forwarded-allow-ips 172.28.0.10
```

That is the backend address assigned to Nginx.

```text
Nginx backend IP
172.28.0.10
        │
        ├── trusted X-Forwarded-For
        └── trusted X-Forwarded-Proto
```

Requests from another source cannot use forwarded headers to rewrite the apparent client address or protocol. Current Uvicorn accepts individual IP addresses and IP networks in `--forwarded-allow-ips`. [Uvicorn](https://www.uvicorn.org/settings/?utm_source=chatgpt.com)

This static address is useful for learning and for a tightly controlled Compose topology. In an orchestrated environment with dynamic proxy addresses, trust is usually configured using a controlled network CIDR or platform-specific proxy identity.

---

# 14. Health-Gated Startup

Nginx declares:

```yaml
depends_on:
  app:
    condition: service_healthy
```

The startup sequence becomes:

```text
1. Build or obtain images
2. Create networks
3. Create volume
4. Start application container
5. Run application readiness health check
6. Wait until application is healthy
7. Start Nginx
```

The short form of `depends_on` waits only for container startup, not application readiness. The `service_healthy` condition makes Compose wait for the dependency’s health check to pass. [Docker Documentation](https://docs.docker.com/reference/compose-file/services/?utm_source=chatgpt.com)

This does not replace runtime resilience. The application may become unavailable after Nginx has started. Nginx must still handle upstream failures with responses such as `502 Bad Gateway`.

Professional wording:

> “Compose uses readiness-gated dependency ordering during startup, while runtime availability remains an independent concern.”

---

# 15. Signal and Shutdown Handling

Both services use:

```yaml
init: true
```

Compose inserts a small init process as PID 1 that forwards signals and reaps child processes. [Docker Documentation](https://docs.docker.com/reference/compose-file/services/?utm_source=chatgpt.com)

The application also uses exec-form `CMD`:

```dockerfile
CMD ["uvicorn", ...]
```

rather than:

```dockerfile
CMD uvicorn ...
```

The exec form avoids an intermediary shell that may prevent the executable from receiving termination signals directly. [Docker Documentation](https://docs.docker.com/reference/cli/docker/container/kill/?utm_source=chatgpt.com)

Shutdown timing is aligned:

```text
Docker stop grace:       30 seconds
Uvicorn graceful limit:  20 seconds
```

```text
Docker sends SIGTERM
    │
    ▼
Init forwards SIGTERM
    │
    ▼
Uvicorn drains requests
    │
    ▼
FastAPI lifespan closes SQLite
    │
    ▼
Process exits before Docker's deadline
```

---

# 16. Read-Only Root Filesystems

Both services use:

```yaml
read_only: true
```

Writable locations are provided explicitly.

## Application

```text
/data   named persistent volume
/tmp    temporary in-memory filesystem
```

## Nginx

```text
/var/cache/nginx   temporary
/var/run           temporary
/tmp               temporary
```

This prevents an application from casually modifying its image filesystem during runtime.

It does not make the system invulnerable. A compromised application can still modify anything writable by its user, including its SQLite database.

Professional wording:

> “The runtime root filesystems are immutable, with explicit writable mounts for persistent and ephemeral state.”

---

# 17. Validate the Compose Model

Before building:

```bash
docker compose config
```

This parses, resolves, and renders the Compose configuration in canonical form. [Docker Documentation](https://docs.docker.com/reference/cli/docker/compose/config/?utm_source=chatgpt.com)

Inspect:

```bash
docker compose config --services
```

Expected:

```text
app
nginx
```

Inspect networks:

```bash
docker compose config --networks
```

Expected shape:

```text
mcp-first-principles_edge
mcp-first-principles_backend
```

---

# 18. Build the Application Image

```bash
docker compose build --pull
```

`--pull` asks Docker to check for newer base-image versions associated with the selected tags.

Expected stages:

```text
builder
├── load Python base
├── copy uv
├── sync dependency layer
├── copy source
└── sync application

runtime
├── load Python base
├── create non-root user
├── copy /app from builder
└── export final image
```

Inspect the image:

```bash
docker image inspect \
  mcp-first-principles-app:local
```

Check its configured user:

```bash
docker image inspect \
  --format '{{.Config.User}}' \
  mcp-first-principles-app:local
```

Expected:

```text
app
```

---

# 19. Start the Stack

```bash
docker compose up --detach
```

Then:

```bash
docker compose ps
```

Expected shape:

```text
NAME                              SERVICE   STATUS
mcp-first-principles-app-1       app       Up (healthy)
mcp-first-principles-nginx-1     nginx     Up (healthy)
```

Follow logs:

```bash
docker compose logs \
  --follow \
  app \
  nginx
```

You should see:

```text
app    | Worker startup started
app    | Application startup completed
nginx  | nginx entered RUNNING state
```

---

# 20. Test the Stack

## Liveness

```bash
curl -i http://127.0.0.1:8080/health/live
```

Expected:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"status":"alive"}
```

## Readiness

```bash
curl -i http://127.0.0.1:8080/health/ready
```

Expected:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"status":"ready","database":"available"}
```

## Default-deny route

```bash
curl -i http://127.0.0.1:8080/debug/process
```

Expected:

```http
HTTP/1.1 404 Not Found
```

## Confirm application bypass is unavailable

```bash
curl -i http://127.0.0.1:8000/health/live
```

Expected:

```text
Connection refused
```

The application container is running, but its port is not published to the host.

---

# 21. Run the MCP Client

Keep:

```python
MCP_URL = "http://127.0.0.1:8080/mcp"
```

Run:

```bash
uv run python test_http_client.py
```

Expected:

```text
Tool discovery succeeds
add returns and persists a record
multiply returns and persists a record
history resource returns calculations
prompt retrieval succeeds
business validation still produces ToolError
```

Docker changed the deployment topology, not the MCP contract.

Professional wording:

> “Containerization is an operational packaging concern; the protocol and application interfaces remain unchanged.”

---

# 22. Verify Data Persistence

First, run calculations through the MCP client.

Then inspect history.

Stop and remove the containers:

```bash
docker compose down
```

Start them again:

```bash
docker compose up --detach
```

Read calculation history again. The old records should remain.

Named volumes exist outside a container’s writable layer and survive container removal unless the volume itself is explicitly deleted. [Docker Documentation](https://docs.docker.com/engine/storage/volumes/?utm_source=chatgpt.com)

```text
Application container removed
        │
        ▼
Container writable layer deleted

Named volume
        │
        └── remains
            calculations.db persists
```

To deliberately delete the data:

```bash
docker compose down --volumes
```

That is destructive.

---

# 23. Image, Container, and Volume

## Image

An immutable runtime template produced by the Docker build:

```text
mcp-first-principles-app:local
```

## Container

A running instance of an image:

```text
mcp-first-principles-app-1
```

## Volume

Persistent storage managed separately from a container:

```text
mcp-first-principles_calculations_data
```

Conceptually:

```text
Dockerfile
    │ build
    ▼
Image
    │ run
    ▼
Container
    │ mounts
    ▼
Volume
```

Professional wording:

> “Images are immutable deployment artifacts, containers are runtime instances, and volumes provide state whose lifecycle is independent of those instances.”

---

# 24. Inspect the Private Network

List networks:

```bash
docker network ls
```

Inspect the backend network:

```bash
docker network inspect \
  mcp-first-principles_backend
```

Expected container addresses:

```text
Nginx:       172.28.0.10
Application: 172.28.0.20
```

Resolve the application service from Nginx:

```bash
docker compose exec nginx \
  getent hosts app
```

Expected:

```text
172.28.0.20 app
```

Test direct backend connectivity from Nginx:

```bash
docker compose exec nginx \
  wget -q -O - \
  http://app:8000/health/live
```

Expected:

```json
{"status":"alive"}
```

This proves:

```text
Service discovery works
Private routing works
Application endpoint works
Nginx can reach upstream
```

---

# 25. Inspect Runtime Identity

Check the application user:

```bash
docker compose exec app id
```

Expected shape:

```text
uid=10001(app) gid=10001(app)
```

Inspect database ownership:

```bash
docker compose exec app \
  ls -la /data
```

Expected shape:

```text
-rw-r--r-- app app calculations.db
```

Try writing to the application directory:

```bash
docker compose exec app \
  sh -c 'touch /app/should-fail'
```

Expected:

```text
Read-only file system
```

Try writing to the data volume:

```bash
docker compose exec app \
  sh -c 'touch /data/should-succeed'
```

Expected: success.

Remove the test:

```bash
docker compose exec app \
  rm /data/should-succeed
```

---

# 26. Failure Experiments

## Experiment 1 — Incorrect Nginx upstream

Change:

```nginx
server app:8000;
```

to:

```nginx
server 127.0.0.1:8000;
```

Recreate Nginx:

```bash
docker compose up \
  --detach \
  --force-recreate \
  nginx
```

Expected:

```http
HTTP/1.1 502 Bad Gateway
```

Diagnosis:

> “Nginx attempted to connect to its own loopback namespace rather than the application service.”

---

## Experiment 2 — Publish the application port

Temporarily add:

```yaml
ports:
  - "127.0.0.1:8000:8000"
```

Now both work:

```text
localhost:8080 → Nginx → application
localhost:8000 → application directly
```

That creates a proxy-bypass path.

Remove the mapping afterward.

---

## Experiment 3 — Break readiness

Set:

```yaml
environment:
  CALC_DB_PATH: /restricted/calculations.db
```

Rebuild or recreate:

```bash
docker compose up \
  --detach \
  --build \
  --force-recreate
```

Expected:

```text
Application startup fails or remains unhealthy
Nginx is not started because service_healthy is unmet
```

This demonstrates startup dependency gating.

---

## Experiment 4 — Stop the application after startup

```bash
docker compose stop app
```

Then:

```bash
curl -i http://127.0.0.1:8080/health/live
```

Expected:

```http
HTTP/1.1 502 Bad Gateway
```

`depends_on` controls Compose startup ordering. It does not continuously remove Nginx whenever the application later becomes unhealthy.

---

## Experiment 5 — Restart without rebuilding

Change Python source and run:

```bash
docker compose restart app
```

The change will not appear because restarting reuses the existing image.

Correct command:

```bash
docker compose up \
  --detach \
  --build \
  app
```

Professional distinction:

```text
Restart
└── Run the same image again

Rebuild
└── Produce a new image from changed source
```

---

## Experiment 6 — Delete the volume

```bash
docker compose down --volumes
docker compose up --detach
```

The database history should be empty.

Diagnosis:

> “The application image and containers remained reproducible, but persistent state was deliberately destroyed with the named volume.”

---

# 27. Why We Still Use One Application Container

The service remains:

```yaml
workers: 1
one app container
one SQLite volume
```

Do not run:

```bash
docker compose up --scale app=4
```

with the current topology.

Problems include:

```text
Several containers
├── need shared SQLite storage
├── perform concurrent writes
├── require Nginx load balancing
└── may run on separate hosts later
```

A local Docker named volume is host-scoped, and SQLite remains a single-file database with constrained concurrent write behavior.

The correct scaling progression is:

```text
Current:
Nginx → one app container → SQLite volume

Later:
Nginx/load balancer
    ├── app replica 1
    ├── app replica 2
    └── app replica 3
             │
             ▼
       PostgreSQL service
```

---

# 28. Coding and Deployment Thought Process

## Step 1: Separate build-time and runtime concerns

```text
Build time
├── Resolve dependencies
├── validate lockfile
├── compile bytecode
└── assemble image

Runtime
├── start Uvicorn
├── open SQLite
└── serve traffic
```

Do not install dependencies every time the container starts.

---

## Step 2: Separate stateless code from state

```text
Image
└── application code and dependencies

Volume
└── calculations.db
```

Rebuilding code must not overwrite production data.

---

## Step 3: Publish only the intended entry point

```text
Published:
Nginx 8080

Not published:
Uvicorn 8000
```

---

## Step 4: Build readiness into dependency ordering

```text
Application started
≠
Application ready
```

Nginx starts only after application readiness succeeds.

---

## Step 5: Align process shutdown

```text
Docker grace period
    >
Uvicorn graceful timeout
```

The outer runtime must allow enough time for the inner runtime to clean up.

---

## Step 6: Make writable state explicit

```text
Persistent:
Docker volume

Ephemeral:
tmpfs

Immutable:
root filesystem
```

---

# Professional Vocabulary

| Term | Meaning |
|---|---|
| **Image** | Immutable container template |
| **Container** | Running instance of an image |
| **Build context** | Files available to the image builder |
| **Build stage** | Named phase within a multi-stage Dockerfile |
| **Runtime stage** | Final image stage used to execute the application |
| **Layer cache** | Reused output from unchanged build instructions |
| **Cache invalidation** | Event causing a layer and later layers to rebuild |
| **Container namespace** | Isolated process, network, and filesystem view |
| **Published port** | Container port mapped to a host address |
| **Service discovery** | Resolving another service by logical name |
| **Bridge network** | Docker-managed local container network |
| **Internal network** | Network without ordinary external routing |
| **Dual-homed proxy** | Proxy connected to two separate networks |
| **Named volume** | Persistent Docker-managed storage |
| **Writable layer** | Temporary per-container filesystem changes |
| **Immutable root filesystem** | Runtime filesystem mounted read-only |
| **Health-gated startup** | Delaying a dependent service until health succeeds |
| **Image provenance** | Evidence identifying how and where an image was built |
| **Proxy bypass** | Reaching an application without passing through its proxy |
| **Supply-chain pinning** | Locking dependency images or tools to known versions or digests |
| **Least privilege** | Granting only the access required to operate |
| **Init process** | PID 1 process that forwards signals and reaps children |
| **Ephemeral state** | State that does not need to survive container replacement |
| **Persistent state** | State whose lifecycle exceeds a container’s lifecycle |

Professional summary:

> “I containerized the MCP service using a cache-aware multi-stage uv build and a non-root, read-only runtime image. Docker Compose now provides private service discovery, readiness-gated startup, persistent SQLite storage, and separate edge and backend networks. Only Nginx publishes a host port; Uvicorn remains reachable exclusively through the isolated backend network.”

# Completion Check

```text
[ ] .dockerignore excludes local environments and runtime data
[ ] uv is pinned to a concrete version
[ ] Dependency installation has its own cached build layer
[ ] Runtime image does not require uv
[ ] Application runs as a non-root user
[ ] Application root filesystem is read-only
[ ] SQLite is stored in a named volume
[ ] Uvicorn binds to 0.0.0.0 inside the container
[ ] Application port 8000 is not host-published
[ ] Nginx reaches the application using app:8000
[ ] Backend network is internal
[ ] Nginx has a fixed trusted backend address
[ ] Nginx starts after application readiness succeeds
[ ] Docker shutdown allowance exceeds Uvicorn's timeout
[ ] MCP client still uses localhost:8080/mcp
[ ] Container replacement does not delete calculation history
[ ] docker compose down --volumes is understood as destructive
```

## Next increment

The next increment hardens the containerized service for realistic remote deployment:

```text
HTTPS client
    │
    ▼
Nginx TLS termination
├── certificate handling
├── security headers
├── request correlation
├── rate limiting
└── authentication boundary
    │
    ▼
FastAPI middleware
├── structured logs
├── request IDs
└── controlled error reporting
    │
    ▼
FastMCP authorization
```

The largest unresolved risk is authentication: the current MCP endpoint remains usable by anyone able to reach port `8080`.