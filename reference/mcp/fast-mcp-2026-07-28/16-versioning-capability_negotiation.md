# Lesson 16 — Versioning and capability discovery

## Outcome

After this lesson, you can distinguish protocol revision, protocol era,
capability support, framework version, and component version.

## Five independent questions

```
Protocol revision  -> which exact wire contract?
Protocol era       -> handshake or modern lifecycle?
Capabilities       -> which optional features are usable?
FastMCP version    -> which framework API and fixes?
Component version  -> which business contract is exposed?
```

Never infer one answer from another.

## The two protocol eras

```
Handshake era through 2025-11-25       Modern era 2026-07-28
--------------------------------       ---------------------
initialize / initialized               no handshake
capabilities exchanged once            client capabilities per request
optional protocol session              no protocol session
server may call client                  MRTR input_required results
```

The `initialize` flow cannot negotiate the modern version. A dual-era client
probes `server/discover`; if unsupported, it may fall back to a supported
handshake revision.

## `server/discover`

A modern server must implement `server/discover`. The result advertises server
identity, supported protocol versions, capabilities, and optional cache hints.
Clients may call it before any other method, but ordinary modern requests remain
self-contained.

Every modern request declares:

- `io.modelcontextprotocol/protocolVersion`;
- `io.modelcontextprotocol/clientCapabilities`;
- normally `io.modelcontextprotocol/clientInfo`.

Every result should identify the server through
`io.modelcontextprotocol/serverInfo`. A version mismatch returns
`UnsupportedProtocolVersionError`; it does not silently reinterpret the request.

## Capabilities are not package detection

A server can run a new FastMCP release without enabling every optional feature.
A client can be new but lack UI support for an extension. Check negotiated
capabilities before use and degrade deliberately.

```
feature required?
  +-- supported -> use it
  +-- optional and absent -> fallback
  +-- required and absent -> clear compatibility error
```

Extensions such as Apps, Tasks, and Skills are opt-in and require both peers to
declare support. Do not present them as universal core behavior.

## FastMCP 4 behavior

FastMCP 4 can serve modern and legacy clients from one application. Its client
can probe modern discovery and fall back to the legacy handshake. This
framework convenience does not merge the two wire models.

The repository lab asserts the selected revision and the negotiation result:

```python
async with Client(mcp, mode="auto") as client:
    assert client.protocol_version == "2026-07-28"
    assert client.session.discover_result is not None
    assert client.initialize_result is None
```

This distinguishes a modern discovery result from a legacy initialization
result; a version string alone does not show which lifecycle ran.

## Hands-on checkpoint

**Execution boundary:**

> In-memory MCP. The same server is contacted once through modern discovery and
> once through the legacy initialization handshake.

Run both protocol eras against one FastMCP application from the repository
root:

```bash
cd reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python compare_protocol_eras.py
```

Expected output:

```
modern: server/discover -> 2026-07-28; no initialize result
legacy: initialize -> 2025-11-25; no discover result
```

The complete runnable exercise is
[`compare_protocol_eras.py`](../labs/compare_protocol_eras.py). Lesson 1's
[`client.py`](../labs/lesson_1/client.py) separately
shows the capabilities attached to an individual modern request.

## Compatibility policy

- Preserve deterministic component names and schemas.
- Prefer additive changes over silently changing semantics.
- Version a business component when its contract breaks.
- Test at least one modern and each supported legacy path.
- Label deprecated features separately from removed features.
- Pin framework and SDK versions in reproducible examples.

**Deprecated** means still represented but discouraged. **Removed** means a
modern peer must not use that method. For example, roots, sampling, and protocol
logging are deprecated; `ping` and `initialize` are removed from the modern
wire contract.

**Say it professionally:**

> Protocol versions establish wire semantics; capabilities establish usable
> features. FastMCP can adapt across protocol eras, but I still test the modern
> and legacy flows independently and version business contracts separately.

## Official references

- [Key changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [Architecture](https://modelcontextprotocol.io/specification/2026-07-28/architecture)
- [FastMCP 4 announcement](https://blog.gofastmcp.com/3mufbh2vcv22o)

