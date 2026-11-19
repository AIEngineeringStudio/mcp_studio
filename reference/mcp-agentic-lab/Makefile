.PHONY: install check test lint format server server-http client agent inspect clean-wire

install:
	uv sync --all-extras

check: lint test

test:
	uv run pytest --cov=mcp_lab --cov-report=term-missing

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

server:
	uv run mcp-lab-server

server-http:
	MCP_LAB_SERVER_TRANSPORT=streamable-http uv run mcp-lab-server

client:
	uv run mcp-lab-client

agent:
	uv run mcp-lab-agent

inspect:
	uv run mcp dev src/mcp_lab/server/app.py

clean-wire:
	find var -type f -name '*.jsonl' -delete

