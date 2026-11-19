"""Typed configuration loaded from MCP_LAB_* environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with safe local-development defaults."""

    model_config = SettingsConfigDict(
        env_prefix="MCP_LAB_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: str = "local"
    service_name: str = "mcp-agentic-lab"
    log_level: str = "INFO"
    log_format: Literal["console", "json"] = "console"
    server_transport: Literal["stdio", "streamable-http"] = "stdio"
    server_host: str = "127.0.0.1"
    server_port: int = Field(default=8000, ge=1, le=65535)
    tracing_enabled: bool = True
    trace_exporter: Literal["none", "console", "otlp"] = "console"
    otlp_endpoint: str = "http://localhost:4317"
    wire_log_enabled: bool = True
    wire_log_path: Path = Path("var/wire.jsonl")
    wire_max_body_bytes: int = Field(default=65_536, ge=1)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
