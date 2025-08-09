# Changelog

All notable changes to this project will be documented in this file.

The format roughly follows Keep a Changelog. Versioning: Semantic Versioning.

## [0.1.0] - 2025-08-09

### Added

- Initial packaged release: async monitoring loop, caching, notifications (Discord, Slack, Email via Apprise).
- CLI flags: --check/--once, --validate, --log-level, --log-json, --log-utc, --self-test, --version.
- Config layering (env + config.json) with validation and notification cooldown.
- Jittered exponential backoff on failures.
- Structured JSON logging and rotating file logs.
- Basic test suite (pytest) for core behaviors.
- Packaging metadata (pyproject.toml), console script entry point.
- Release & installation docs, badges, CONTRIBUTING guide, roadmap.

