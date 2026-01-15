# Claude Time Proxy

A FastAPI-based HTTP proxy that sits between Claude CLI clients and the Anthropic API, enforcing time-based access control and user authentication.

## Features

- **Time-based access control**: Restrict API access to specific days and hours
- **User authentication**: Validate client API keys against a users file
- **Access logging**: Log first and last access per user in each time period with request counts

## Installation

```bash
# Clone the repository
git clone https://github.com/breed/claude-time-proxy.git
cd claude-time-proxy

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

## Configuration

### Environment Variables

Create a `.env` file (see `.env.example`):

```bash
CLAUDE_PROXY_ANTHROPIC_API_KEY=sk-ant-...  # Your Anthropic API key
CLAUDE_PROXY_SCHEDULE_FILE=schedule.txt     # Path to schedule file
CLAUDE_PROXY_USERS_FILE=users.txt           # Path to users file
CLAUDE_PROXY_HOST=0.0.0.0                   # Server host (default: 0.0.0.0)
CLAUDE_PROXY_PORT=8080                      # Server port (default: 8080)
```

### Schedule File

Create `schedule.txt` to define when access is allowed (see `schedule.example.txt`):

```
# Weekdays 9am-5pm
Mon,Tue,Wed,Thu,Fri 09:00-17:00

# Saturday morning
Sat 10:00-14:00
```

Format:
- Each line: `DAYS HH:MM-HH:MM`
- Days: Comma-separated list (Mon,Tue,Wed,Thu,Fri,Sat,Sun)
- Times: 24-hour format, local timezone
- Lines starting with `#` are comments

### Users File

Create `users.txt` to define authorized users (see `users.example.txt`):

```
alice@example.com sk-alice-random-key-12345
bob@example.com sk-bob-another-key-67890
```

Format:
- Each line: `EMAIL KEY`
- The KEY is what users will set as their API key on client machines

## Running the Server

```bash
# Using the module
python -m claude_time_proxy.main

# Or using uvicorn directly
uvicorn claude_time_proxy.main:app --host 0.0.0.0 --port 8080
```

## Client Configuration

On client machines, configure Claude CLI to use the proxy:

```bash
export ANTHROPIC_BASE_URL=http://your-proxy-host:8080
export ANTHROPIC_API_KEY=sk-alice-random-key-12345  # Key from users.txt
```

## API Endpoints

- `GET /health` - Health check
- `GET /schedule` - View current schedule status
- `/v1/*` - Proxied Claude API endpoints

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run specific tests
pytest tests/test_users.py -v
```

## License

MIT
