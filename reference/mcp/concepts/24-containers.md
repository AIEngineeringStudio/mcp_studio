# Docker packaging and networking

**Outcome:** Explain image, container, network, and volume boundaries without confusing them with MCP.

**Prerequisites:** [18: Uvicorn, workers, and process state](18-process-runtime.md), [22: Reverse proxies and TLS](22-proxy-tls.md), [23: Configuration and reproducible environments](23-configuration.md).

## Package the environment

An image is a packaged filesystem and runtime configuration. A container is a
running instance of that image. A volume stores data independently of a
container's writable layer.

```
host port --> proxy container --> app container --> database
                                      |
                              persistent storage
```

Containerization packages the application and dependencies. It does not change
`tools/call` into a different protocol.

## Network namespaces change localhost

Inside the application container, `127.0.0.1` refers to that container's own
network namespace. It does not identify a database container or the Mac host.
Compose service names can provide addresses on the Compose network.

An application may need to listen on `0.0.0.0` inside its container to receive
traffic from the proxy container. Publishing a port to the host is a separate
decision. A private backend listener does not require exposing that port on
every host interface.

## Build versus run

Dependency installation belongs in the build. Use the lockfile and exact
versions, then copy application source. Copying dependency metadata before
source often allows layer caching when only application code changes.

Exclude `.env`, local virtual environments, caches, and credentials from the
build context. Running a container with runtime environment variables is
different from baking those values into an image layer.

Use a non-root runtime user and declare intentional writable locations.
A read-only root filesystem is useful only if the application can write its
required temporary and persistent data elsewhere.

## Health and readiness

Starting the database container does not prove the database is ready.
A service may need a readiness check and bounded connection startup policy.
A health check should test the appropriate responsibility without exposing
private internal data.

Coordinate container termination grace with the HTTP runtime's graceful
shutdown so active requests have a deliberate completion window.

## Two Mac architectures

Use a base image that publishes both `linux/amd64` and `linux/arm64` variants.
Native container runs select the matching platform; explicit cross-platform
builds can target both. Emulation may help compatibility testing but does not
represent native performance.

This guide describes a production extension. It does not supply an untested
Docker deployment or require Docker for the basic labs.

## Failure walkthrough

A recreated application container should not erase durable ticket records.
If it does, data was probably stored only in the container's writable layer.
Conversely, deleting a volume intentionally removes persistent data; avoid
using destructive volume removal as routine cleanup in a learning exercise.

**Professional articulation:**

> “The image captures the runtime environment; volumes preserve state, and
> network configuration controls which service boundaries are reachable.”

## Sources and next step

- [Archive: conversations/chatgpt/9_Docker_DockerCompose.md](../../conversations/chatgpt/9_Docker_DockerCompose.md)
- [Archive: _learning_resources/troubleshoot.md](../../_learning_resources/troubleshoot.md)
- [Official reference](https://docs.docker.com/build/building/multi-platform/) — checked 2026-11-15.

Next: [Timeouts, cancellation, retries, and idempotency](25-reliability.md).

