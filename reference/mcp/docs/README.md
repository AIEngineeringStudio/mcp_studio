# Streamable HTTP basics

Run these commands from the `streamable_http_basics` directory.

### Run Server

```shell
uv run mcp-studio-server
```

### Run Client

```shell
uv run mcp-studio-client \
  --url http://127.0.0.1:8000/mcp/ \
  --tool add \
  --arguments '{"a":20,"b":22}'
```
