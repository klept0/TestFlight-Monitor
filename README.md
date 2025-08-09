# TestFlight Monitor

A lightweight Python CLI tool to monitor [Apple TestFlight](https://testflight.apple.com/) invite codes for open slots, with notification support via [Apprise](https://github.com/caronc/apprise).

---

## Features

- Monitor multiple TestFlight codes for open slots
- Apprise notifications (push, email, Discord, etc.)
- Structured / JSON logging support
- Graceful shutdown via signals
- One-off check mode (`--check`)


---

---

## Requirements

- Python 3.8+
- [Pillow](https://pypi.org/project/Pillow/)
- [requests](https://pypi.org/project/requests/)
- [apprise](https://pypi.org/project/apprise/)

Install dependencies:

```sh
pip install -r requirements.txt
```

## CLI Usage

The application exposes both a continuous monitor loop and one-off checks.

Basic help:

```sh
python -m main --help
```

Run continuous monitoring (default interval from config / env):

```sh
python -m main
```

Run a single check and exit:

```sh
python -m main --check
```

Validate configuration only:

```sh
python -m main --validate
```

Optional flags:

- `--log-level DEBUG` for verbose logging
- `--log-utc` to output timestamps in UTC ISO-8601
- `--once` alias for `--check`

## Configuration

Configuration is loaded from environment variables and an optional `config.json`.

`config.json` example:

```json
{
	"app_ids": ["FAKECODE", "ANOTHER"],
	"check_interval_seconds": 300,
	"cache_ttl_minutes": 5,
	"notifications": {
		"discord_webhook_url": "https://discord.com/api/webhooks/.../..."
	}
}
```

Environment variable overrides (comma-separated where applicable):

| Variable | Purpose |
|----------|---------|
| TESTFLIGHT_APP_IDS | Comma list of app codes |
| CHECK_INTERVAL_SECONDS | Override interval between cycles |
| CACHE_TTL_MINUTES | Cache TTL for per-app results |
| DISCORD_WEBHOOK_URL | Discord notifications |
| SLACK_WEBHOOK_URL | Slack notifications |
| EMAIL_* | Email notification settings |
| LOG_LEVEL | Log level (fallback) |
| LOG_FILE | Log filename |

## Logging

Logs are written to `logs/testflight_monitor.log` (rotating, 10MB x5) and console.
Set level via `--log-level`, `LOG_LEVEL`, or `TFM_LOG_LEVEL` env var.

Structured JSON logs (one line per event) for ingestion:

```sh
python -m main --log-json
```

or set `TFM_LOG_JSON=1`.

Enable UTC timestamps:

```sh
python -m main --log-utc
```

## Notifications

Notifications use [Apprise](https://github.com/caronc/apprise). Configure any combination of Discord, Slack, or Email. Rate limiting prevents spam (per app ID minimal interval 10 minutes in sample).

## Testing

Run tests (requires pytest):

```sh
pytest -q
```

The tests mock network calls; no external HTTP traffic is performed.

## Future Enhancements

- Advanced HTML parsing (structured) for higher accuracy
- Async test fixtures for richer simulation

---

## Minimal Deployment

This repository now contains only runtime essentials:

- `main.py`, `monitor.py`, `notifications.py`, `config.py`
- `config.json` (edit with your values)
- `requirements.txt`
- `README.md`, `LICENSE`

Development helper files (Makefile, CI workflow, sample config, editor configs) were removed for a lean production footprint. Reintroduce them as needed in a fork if you require automated linting or formatting.

To enable structured JSON logs:

```sh
python -m main --log-json
```

Basic run:

```sh
python -m main --log-level INFO
```

Single check:

```sh
python -m main --check
```

Update `config.json` or use environment variables (`TESTFLIGHT_APP_IDS`, etc.) to configure behavior.

---

## Quick Start (Ready for Use)

1. Populate `config.json` (or set `TESTFLIGHT_APP_IDS`). At minimum:

```json
{ "app_ids": ["YOURCODE" ] }
```
2. Install dependencies:

```sh
pip install -r requirements.txt
```
3. Run continuous monitoring:

```sh
python -m main --log-level INFO
```
4. (Optional) Structured logs:

```sh
python -m main --log-json --log-utc
```
5. One-off check:

```sh
python -m main --check
```

Environment-only setup (no config file):

```sh
export TESTFLIGHT_APP_IDS=CODE1,CODE2
python -m main
```

The application is now production-ready in CLI form (GUI removed). Add your preferred Apprise notification endpoints via env or `config.json` to receive alerts when availability appears.

