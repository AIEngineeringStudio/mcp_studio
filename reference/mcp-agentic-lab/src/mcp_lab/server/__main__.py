"""Run the example server over stdio or Streamable HTTP."""

import uvicorn

from mcp_lab.observability import configure_logging, configure_tracing, get_logger, get_settings
from mcp_lab.server.app import create_server
from mcp_lab.wire import JsonlWireRecorder
from mcp_lab.wire.http_middleware import JsonRpcHTTPRecorderMiddleware


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    configure_tracing(settings)
    logger = get_logger(__name__)
    server = create_server(settings)

    if settings.server_transport == "stdio":
        logger.info("server_starting", transport="stdio")
        server.run(transport="stdio")
        return

    logger.info(
        "server_starting",
        transport="streamable-http",
        host=settings.server_host,
        port=settings.server_port,
    )
    app = server.streamable_http_app(json_response=True, stateless_http=True)
    recorder = JsonlWireRecorder("var/http-wire.jsonl", enabled=settings.wire_log_enabled)
    observed_app = JsonRpcHTTPRecorderMiddleware(
        app, recorder, max_bytes=settings.wire_max_body_bytes
    )
    uvicorn.run(observed_app, host=settings.server_host, port=settings.server_port)


if __name__ == "__main__":
    main()
