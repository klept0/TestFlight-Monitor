<!-- CONTRIBUTING formatting normalized -->
# Contributing Guide

Thanks for your interest in improving TestFlight-Monitor! This document explains how to set up a development environment, the project conventions, and how to propose changes.

---

## Table of Contents

1. Project Scope & Philosophy
2. Quick Start (Dev Mode)
3. Configuration & Secrets
4. Running the Monitor / Modes
5. Tests & Coverage
6. Code Style & Tooling
7. Logging & Observability
8. Notifications & Rate Limiting
9. Commit & PR Guidelines
10. Dependency Management
11. Release Checklist
12. Roadmap / Enhancement Ideas
13. Support & Questions

---

## 1. Project Scope & Philosophy

Lightweight, dependency‑minimal CLI to monitor Apple TestFlight invite codes for availability and send notifications via Apprise. Goals: clarity, reliability, low operational overhead. Non-goals: heavy web scraping frameworks, GUI, or persistence layers.

---

## 2. Quick Start (Dev Mode)

```sh
git clone https://github.com/klept0/TestFlight-Monitor.git
cd TestFlight-Monitor
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

Self-check (no network):

```sh
python -m main --self-test
```

Run tests:

```sh
pytest -q
```

Run monitor (example):

```sh
export TESTFLIGHT_APP_IDS=CODE1,CODE2
python -m main --log-level INFO
```

---

## 3. Configuration & Secrets

Configuration sources (precedence: env > config.json defaults):

* `config.json` – Checked into repo for local overrides (avoid committing real secrets).
* Environment variables (see README table) override file settings.
* Avoid embedding tokens directly in code; use env injection for CI / production.

Never commit API keys / webhook secrets. If a secret is accidentally committed: rotate it and force-push removal if necessary.

---

## 4. Running the Monitor / Modes

* Continuous monitoring (default): `python -m main`
* Single check: `python -m main --check`
* Config validation: `python -m main --validate`
* Dry self-test (no external HTTP): `python -m main --self-test`

Backoff: Exponential with jitter on errors; interval resets on success.

---

## 5. Tests & Coverage

* Framework: `pytest`
* Tests should avoid real network I/O (mock `_fetch_availability`).
* Consider adding coverage thresholds (e.g., 85%) once test breadth increases.
* Add regression tests for bug fixes before or alongside the fix when possible.

---

## 6. Code Style & Tooling

| Tool | Purpose | Status |
|------|---------|--------|
| `ruff` | Linting (and optional formatting) | Enabled in CI |
| `mypy` | Static type checking | Enabled (lenient) |
| `coverage` | Test coverage reporting | Enabled (report only) |

Guidelines:

* Prefer type hints on public functions.
* Keep functions small & single‑purpose.
* Avoid premature abstraction; duplicate *small* logic if it increases clarity.
* Logging: use structured JSON mode for automation pipelines when needed (`--log-json`).

---

## 7. Logging & Observability

* Default human-readable logs to console + rotating file `logs/testflight_monitor.log` (10MB x5).
* Enable JSON logging with `--log-json` or `TFM_LOG_JSON=1`.
* UTC timestamps: `--log-utc`.
* Future: optional metrics endpoint / OpenTelemetry (see Roadmap).

---

## 8. Notifications & Rate Limiting

Implemented via [Apprise](https://github.com/caronc/apprise). Supported channels (based on config): Discord, Slack, Email.

* Per-app cooldown: default 600s. Override with `TFM_NOTIFY_COOLDOWN`.
* Avoid rapid loops spamming endpoints: respect cooldown or implement queue escalation if future multi-channel burst logic is added.

Enhancement ideas: batched summaries, failure notices, structured embed formatting.

---

## 9. Commit & PR Guidelines

* Create feature branches: `feature/<short-description>` or `fix/<issue-id>`.
* Keep commits logically grouped; rebase / squash noisy WIP commits before PR.
* Commit messages:
  * Short (<= 72 char) imperative summary line.
  * Optional body paragraphs for rationale / tradeoffs.
* Reference related issues (e.g., `Closes #12`).
* CI must be green (lint + mypy + tests) before merge.

PR Checklist:

* [ ] Tests added/updated (if logic changed)
* [ ] README updated (if user-facing behavior changed)
* [ ] No stray debug prints
* [ ] No secrets / tokens committed

---

## 10. Dependency Management

* Runtime deps: declared in `requirements.txt` (pin if reproducibility becomes critical, otherwise allow floating minor updates initially).
* Avoid large frameworks; prefer standard library or lightweight libs.
* Security review: periodically run `pip-audit` (candidate for CI inclusion later).

Adding a dependency? Ask:

1. Does stdlib solve it acceptably?
2. Does this add a transitive chain of risky packages?
3. Is the license compatible (MIT / BSD / Apache preferred)?

---

## 11. Release Checklist

1. Update version (if versioning added to `pyproject.toml`).
2. Regenerate / verify `requirements.txt` (if pinned).
3. Run full test suite + self-test.
4. Confirm README examples still match CLI output.
5. Tag release: `git tag -a vX.Y.Z -m "Release vX.Y.Z" && git push --tags`.
6. Draft release notes (changes, notable fixes, breaking changes, upgrade notes).

---

## 12. Roadmap / Enhancement Ideas

These are the previously public “Recommended Enhancements” now tracked for contributors:

1. CI expansion: code coverage threshold enforcement; optionally upload to Codecov.
2. Security scans: integrate `pip-audit` or `safety`.
3. Packaging: enrich `pyproject.toml` with metadata & console script entry point.
4. Structured parsing: replace heuristic keyword scan with more resilient HTML / JSON extraction if endpoints stabilize.
5. Metrics: optional Prometheus / OpenTelemetry exporter.
6. Retry / circuit breaking: track consecutive failures & short‑circuit noisy endpoints.
7. Notification templating: per-channel formatting + batch summary mode.
8. Config schema validation library (e.g., `pydantic` optional extra) for stricter errors.
9. CLI enhancements: `--list` to show current cache state, `--export` to dump last results JSON.
10. Plugin system for additional notification channels without modifying core.
11. Docker image with multi-arch build (slim, non-root).
12. Automatic pruning of old log files beyond rotation window.
13. Add concurrency limiting for large app_id lists.
14. Integrate ruff formatting (`ruff format`) consistently.
15. Introduce a CONTRIBUTING-driven issue template & PR template.

Feel free to open issues proposing refinements or new ideas—be clear about problem statement vs. solution.

---

## 13. Support & Questions

Open a GitHub Issue for:

* Bugs (include reproduction steps + logs if possible)
* Feature proposals (state the user need first)
* Documentation gaps

For security disclosures: do **not** open a public issue—consider adding a SECURITY.md (TODO if sensitive vectors discovered).

---

Happy monitoring!
