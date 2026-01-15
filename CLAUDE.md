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
```

## Architecture

```
src/claude_time_proxy/
├── main.py      # FastAPI app, routes, lifespan management
├── config.py    # Pydantic settings, loads from env vars (CLAUDE_PROXY_* prefix)
├── schedule.py  # Schedule file parsing and time window logic
└── proxy.py     # HTTP proxying to Anthropic API (handles streaming)
```

**Request flow:** Client → `/v1/{path}` route → `check_access()` → `proxy_request()` → Anthropic API

## Configuration

Environment variables with `CLAUDE_PROXY_` prefix. See `.env.example`.

- `ANTHROPIC_API_KEY` - Required. The actual API key stored on the proxy.
- `SCHEDULE_FILE` - Path to schedule configuration file (default: `schedule.txt`)

### Schedule file format

See `schedule.example.txt`. Each line specifies a time period when access is allowed:

- Lines have the form: `DAYS HH:MM-HH:MM`
- DAYS are a comma-separated list (Mon,Tue,Wed,Thu,Fri,Sat,Sun)
- Times are in 24-hour format, local timezone
- Lines starting with # are comments
- Blank lines are ignored

Example:
```
Mon,Tue,Wed,Thu,Fri 09:00-17:00
Sat 10:00-14:00
```

## Client Configuration

On remote machines, configure Claude CLI to use this proxy:
```bash
export ANTHROPIC_BASE_URL=http://your-proxy-host:8080
export ANTHROPIC_API_KEY=dummy  # proxy handles the real key
```
