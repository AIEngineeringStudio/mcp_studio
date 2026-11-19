# Lesson 16 — Versioning and capability discovery

## Outcome

After this lesson, you can distinguish protocol revision, protocol era,
capability support, framework version, and component version.

## Five independent questions

```text
Protocol revision  -> which exact wire contract?
Protocol era       -> handshake or modern lifecycle?
Capabilities       -> which optional features are usable?
FastMCP version    -> which framework API and fixes?
Component version  -> which business contract is exposed?
```

Never infer one answer from another.

## The two protocol eras

```text
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

```text
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

The repository lab asserts the selected modern revision:

```python
assert client.protocol_version == "2026-07-28"
```

Run it over all three boundaries:

```bash
cd reference/mcp/labs
uv run python client.py memory
uv run python client.py stdio
```

For HTTP, start `uv run python server.py --http` in another terminal, then run:

```bash
uv run python client.py http
```

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

