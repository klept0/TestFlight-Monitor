# TestFlight Monitor

A cross-platform Python GUI app to monitor [Apple TestFlight](https://testflight.apple.com/) invite codes for open slots, with notification support via [Apprise](https://github.com/caronc/apprise).  
The app features a modern, resizable Tkinter interface with dark/light mode, dynamic status display, and heartbeat notifications.

---

## Features

- **Monitor multiple TestFlight codes** for open slots
- **Desktop GUI** with dynamic resizing and dark/light mode
- **Apprise notifications** (push, email, Discord, etc.)
- **Heartbeat notification** every 6 hours to confirm the app is running
- **Manual and automatic status updates**
- **Add/remove codes** via menu
- **Edit Apprise settings** in-app
- **Minimize to taskbar or (optionally) system tray**
- **No credentials hardcoded**—all settings are editable and saved locally


---

## Screenshots

![light mode](https://github.com/user-attachments/assets/e0fe4664-8760-46a9-bf4d-9e47200beb34)
![dark mode](https://github.com/user-attachments/assets/e47a896f-bec7-4e30-ab7e-beb2549128b7)

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
- GUI integration improvements & packaging
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

