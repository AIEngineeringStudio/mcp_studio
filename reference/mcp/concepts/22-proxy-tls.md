# Reverse proxies and TLS

**Outcome:** Explain where a proxy sits and diagnose route, trust, and buffering failures.

**Prerequisites:** [11: Streamable HTTP](11-streamable-http.md), [18: Uvicorn, workers, and process state](18-process-runtime.md), [19: Host validation, Origin, and CORS](19-origin-cors.md).

## Put a controlled entry point in front

A reverse proxy accepts incoming requests and forwards them to an internal
application. It can handle TLS certificates, route paths, apply limits, and
balance traffic. TLS encrypts communication and supports server identity
verification.

```
Client -- HTTPS --> reverse proxy -- HTTP or HTTPS --> application
                         |
                 certificate and routing
```

The internal hop is a separate trust decision. An untrusted network may require
encryption there too. TLS does not determine which ticket a user may access.

## Follow the path exactly

A client calls `https://support.example/mcp`. The proxy forwards the intended
path to the application's MCP endpoint. If a mount already adds `/mcp` and
the child application adds another `/mcp`, the resulting route can become
`/mcp/mcp`.

Trailing slashes and path replacement in proxy configuration matter. Start
with one explicit route and test it with an MCP client. A health endpoint can
work while the MCP path is wrong.

## Preserve trust deliberately

Forwarded headers can describe the original scheme and client address.
Only trust them from known proxies. If arbitrary callers can supply trusted
forwarded identity information, logs and security decisions can be misleading.

Keep the application listener private when the proxy is intended to be the
only entry point. Otherwise callers can bypass controls implemented only at
the proxy.

## Buffering and timeout behavior

For SSE responses, response buffering can delay visible updates. Configure
streaming behavior for the intended endpoint and verify arrival times at the
client. Request buffering and response buffering are different controls.

Timeouts also have different meanings. An upstream connection timeout,
an idle read timeout, and an application's total operation deadline are not
interchangeable. A periodic event can keep an idle timeout satisfied while
the operation exceeds its intended total budget.

## Safe retries

A proxy automatically retrying a write can cause duplicate effects. Evaluate
upstream retry settings alongside application idempotency. A dropped connection
after commit is an uncertain outcome, not proof that the operation failed.

The archived file named `8_Ngnix_ReverseProxy.md` actually contains the
testing lesson. Use the catalog's correction and the official proxy reference.

## Failure walkthrough

If events arrive only at completion, compare direct application access with
proxy access in a controlled local test. If only the proxy path batches them,
inspect buffering before rewriting the tool.

## Read a minimal proxy route

This Nginx fragment is illustrative; production TLS, limits, trusted headers,
and timeouts require a complete reviewed configuration:

```nginx
location /mcp {
    proxy_pass http://mcp_app:8765/mcp;
    proxy_http_version 1.1;
    proxy_buffering off;
}
```

`location /mcp` matches the public path. `proxy_pass` selects the internal
application address. `mcp_app` is a network name, not an MCP server name from
the protocol. Turning response buffering off can be necessary for timely
stream events, but it does not create progress events or make retries safe.

**Professional articulation:**

> “The proxy owns the external HTTP boundary. We verify path mapping,
> forwarded-header trust, streaming behavior, and retry policy independently.”

## Sources and next step

- [Archived Docker and proxy example](../fastMcp-fastApi-uvicorn-ngnix-docker/9_Docker_DockerCompose.md)
- [Archived TLS, authentication, and observability example](../fastMcp-fastApi-uvicorn-ngnix-docker/10_TLS_AuthN_AuthZ_Observability.md)
- [Archived proxy-streaming notes](../../../_archive/streamable/streamable-7.md)
- [Official reference](https://nginx.org/en/docs/http/ngx_http_proxy_module.html) — checked 2026-11-15.

Next: [Configuration and reproducible environments](23-configuration.md).

