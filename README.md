# TestFlight Monitor

![Status](https://github.com/klept0/TestFlight-Monitor/actions/workflows/ci.yml/badge.svg)
![Python Versions](https://img.shields.io/badge/python-3.10--3.13-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Coverage](https://img.shields.io/badge/coverage-unknown-lightgrey)
![Lint: Ruff](https://img.shields.io/badge/lint-ruff-%23cc7722)
![Types: mypy](https://img.shields.io/badge/types-mypy-informational)

A lightweight Python CLI tool to monitor [Apple TestFlight](https://testflight.apple.com/) invite codes for open slots, with notification support via [Apprise](https://github.com/caronc/apprise).

---

## Features

- Monitor multiple TestFlight codes for open slots
- Apprise notifications (push, email, Discord, etc.)
- Structured / JSON logging support
- Graceful shutdown via signals
- One-off check mode (`--check`)

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
- `--self-test` run an internal dry run (config + simulated cycle) and exit

## Configuration

Configuration is loaded from environment variables and an optional `config.json`.

`config.json` example:

```json
{ "app_ids": ["FAKECODE", "ANOTHER"], "check_interval_seconds": 300, "cache_ttl_minutes": 5, "notifications": { "discord_webhook_url": "https://discord.com/api/webhooks/.../..." } }
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
| TFM_NOTIFY_COOLDOWN | Seconds between notifications for same app (default 600) |
| TFM_LOG_JSON | Force JSON logs if set (1/true) |

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

Notifications use [Apprise](https://github.com/caronc/apprise). Configure any combination of Discord, Slack, or Email. Per-app cooldown defaults to 600s (override via `TFM_NOTIFY_COOLDOWN`).

## Testing

Run tests (requires pytest):

```sh
pytest -q
```

The tests mock network calls; no external HTTP traffic is performed.

To publish real coverage to a service (Codecov or Coveralls), add their action after the coverage report step and update the Coverage badge to reflect the service URL.

## Future Enhancements

- Advanced HTML parsing (structured) for higher accuracy
- Async test fixtures for richer simulation

---

## Repository Layout

Current repository contents (lean runtime + minimal scaffolding):

- `main.py`, `monitor.py`, `notifications.py`, `config.py`
- `config.json` (active configuration)
- `config.sample.json` (copy & edit to create `config.json`)
- `requirements.txt`
- `README.md`, `LICENSE`
- `.editorconfig` (basic formatting guidance)
- Optional stubs: `Makefile`, `pyproject.toml` (currently placeholders)
- `.github/workflows/ci.yml` (basic CI example; expand as needed)

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

## Quick Start

- Populate `config.json` (or set `TESTFLIGHT_APP_IDS`). At minimum:

```json
{ "app_ids": ["YOURCODE" ] }
```

- Install dependencies:

```sh
pip install -r requirements.txt
```

- Run continuous monitoring:

```sh
python -m main --log-level INFO
```

- (Optional) Structured logs:

```sh
python -m main --log-json --log-utc
```

- One-off check:

```sh
python -m main --check
```

Environment-only setup (no config file):

```sh
export TESTFLIGHT_APP_IDS=CODE1,CODE2
python -m main
```

The application is now production-ready in CLI form (GUI removed). Add your preferred Apprise notification endpoints via env or `config.json` to receive alerts when availability appears.

---

## License

This project is released under the MIT License. See `LICENSE` for details.

## Release & Installation

Current version: 0.1.0 (alpha).

Install from source (until published to PyPI):

```sh
git clone https://github.com/klept0/TestFlight-Monitor.git
cd TestFlight-Monitor
python -m venv .venv && source .venv/bin/activate
pip install .[dev]  # or: pip install .
testflight-monitor --help
```

Planned PyPI install (after publishing):

```sh
pip install testflight-monitor
testflight-monitor --help
```

Cutting a release:

1. Update `__version__` in `__init__.py` & `[project] version` in `pyproject.toml`.
2. Update badges / README examples if needed.
3. Commit: `git commit -am "chore: release vX.Y.Z"`.
4. Tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z" && git push --tags`.
5. Build & upload (once on PyPI):

```sh
python -m build
twine upload dist/*
```


<!-- End of public README -->
