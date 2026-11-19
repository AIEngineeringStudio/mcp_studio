# Configuration and reproducible environments

**Outcome:** Separate configuration from code and validate required production settings at startup.

**Prerequisites:** [07: The first client and in-memory testing](07-in-memory-client.md), [17: Application lifespan and dependency ownership](17-application-lifespan.md).

## One application, several environments

The ticket service might use a fixture locally and a database in deployment.
Source code should not contain real credentials or assume a machine-specific
path. Configuration provides values that vary between environments.

Environment variables are strings supplied to a process. A `.env` file is
a local convenience for populating configuration; it is not a secret vault.
Typed settings convert and validate those values into a consistent model.

```
environment / local .env
          |
       validation
          |
      Settings object
          |
     application startup
```

## Progress from a minimal exercise

The first MCP lab needs no secrets or database URL. Introducing typed settings
there would obscure its main concept. Once the production extension has a
database, issuer, allowed origins, and timeouts, centralized validation solves
a real problem.

For this workspace's production style, load local environment values with
python-dotenv and define a pydantic-settings model. Keep required fields
required; a missing production credential should not silently fall back to a
demo value.

## Fail early and explain the field

If a timeout expects a positive number but receives `"tomorrow"`, startup
should fail with the setting name. Do not let the first user's request
discover invalid configuration.

Avoid dumping the entire settings object into logs. A useful validation error
names a field without exposing its secret value.

Document precedence so users know whether a process environment value
overrides a local file. Test that precedence rather than relying on memory
of a library default.

## Reproducibility has several layers

An exact direct dependency pin identifies the requested package release.
A lockfile records resolved transitive dependencies. A Python version selects
the runtime. A container base image adds operating-system dependencies.

The lab keeps a separate project manifest and lockfile. Updating a dependency
should be a deliberate change followed by the relevant contract tests.
“Latest” on a moving documentation site is not a reproducible environment.

## Intel and Apple Silicon

The Python source should work on both Macs. Native dependencies need compatible
wheels or a working build toolchain for each architecture. Resolving a lockfile
on one Mac does not prove every package installs successfully on the other.

Keep architecture differences in environment setup rather than changing
business logic. Record which platform was actually tested.

**Worked failure:**

> The database URL is omitted. Startup fails before readiness, with a message
> identifying the missing URL. The service never accepts a ticket request
> against an unintended fallback database.

## See typed startup configuration

This is the production-extension pattern used after configuration has become a
real requirement:

```python
from pydantic import PositiveFloat
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    request_timeout_seconds: PositiveFloat

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
```

The two fields have no defaults, so they are required. `PositiveFloat` rejects
zero, negative numbers, and nonnumeric text. Create `Settings()` once during
startup; do not scatter unvalidated `os.getenv` calls through tool handlers.

Keep real `.env` files out of version control. Commit a `.env.example` with
placeholder names when developers need to know which values to supply.

**Professional articulation:**

> “We validate configuration once at startup and preserve exact dependency
> resolution so environment changes are reviewable and reproducible.”

## Sources and next step

- [Archived MCP walkthrough](../walk-through-docs/walkthrough_doc.md)
- [Archived MCP notes](../../temp/mcp_notes.md)
- [Archived troubleshooting notes](../../temp/troubleshoot.md)
- [Official reference](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — checked 2026-11-15.

Next: [Docker packaging and networking](24-containers.md).

