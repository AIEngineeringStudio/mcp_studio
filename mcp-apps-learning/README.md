## Development Environment

```shell
cd mcp-apps-learning
```

```shell
uv sync --locked
```

### `mcp run`

For **Streamable HTTP**, use `mcp run`, not `mcp dev`:

```shell
uv run --locked mcp run customer_server.py --transport streamable-http
```

### `mcp dev`

`mcp dev` launches the MCP Inspector and connects to your server over `stdio`.

```bash
uv run --locked mcp dev customer_server.py
```

```shell
uv run --with mcp==2.2.0 mcp run customer_server.py
```

Alternatively, make the transport explicit inside `customer_server.py`:

```python
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```
