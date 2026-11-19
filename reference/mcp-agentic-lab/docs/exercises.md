# Practice path

1. Run `mcp-lab-client` and reconstruct discovery, tool listing, and tool call
   ordering from `var/wire.jsonl`.
2. Run the same interaction over Streamable HTTP and compare `http-wire.jsonl`.
3. Add a typed `multiply` tool and inspect the schema in `tools/list`.
4. Divide by zero. Compare raw wire, server middleware, and client facade records.
5. Add a secret-looking argument and test redaction at every observation layer.
6. Use JSON logs and correlate a `trace_id` with a console-exported span.
7. Implement `AgentModel` for your preferred model provider and translate the MCP
   `input_schema` values into that provider's tool format.
8. Add a policy layer that asks a user before non-read-only tool calls.
9. Connect a second MCP server and route across both tool catalogs.
10. Export traces to a collector and graph client, transport, server, and tool latency.

