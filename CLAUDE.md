# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Time Proxy is a FastAPI-based HTTP proxy that sits between Claude CLI clients and the Anthropic API, enforcing time-based access control. It allows administrators to restrict Claude API access to specific days and hours.

## Commands

```bash
# Install dependencies
pip install -e .
pip install -e ".[dev]"  # with dev dependencies

# Run the server
python -m claude_time_proxy.main
# or after installation:
# uvicorn claude_time_proxy.main:app --host 0.0.0.0 --port 8080

# Run tests
pytest
pytest tests/test_schedule.py -v  # single test file
pytest -k "test_allowed"          # tests matching pattern

# Type checking (if added)
# mypy src/
```

## Architecture

```
src/claude_time_proxy/
├── main.py      # FastAPI app, routes, lifespan management
├── config.py    # Pydantic settings, loads from env vars (CLAUDE_PROXY_* prefix)
├── schedule.py  # Time window logic (is_access_allowed, get_schedule_status)
└── proxy.py     # HTTP proxying to Anthropic API (handles streaming)
```

**Request flow:** Client → `/v1/{path}` route → `check_access()` (schedule + bypass key) → `proxy_request()` → Anthropic API

## Configuration

All settings via environment variables with `CLAUDE_PROXY_` prefix. See `.env.example`.

Key settings:
- `ANTHROPIC_API_KEY` - Required. The actual API key stored on the proxy.
- `ALLOWED_DAYS` - JSON array of weekday numbers (0=Monday, 6=Sunday)
- `START_HOUR`/`END_HOUR` - 24-hour format time window
- `TIMEZONE` - IANA timezone name for schedule evaluation
- `BYPASS_KEY` - Optional header key (`x-bypass-key`) to skip time checks

## Client Configuration

On remote machines, configure Claude CLI to use this proxy:
```bash
export ANTHROPIC_BASE_URL=http://your-proxy-host:8080
export ANTHROPIC_API_KEY=dummy  # proxy handles the real key
```
