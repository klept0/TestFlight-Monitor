import asyncio
import logging
import signal
import sys
import os
import time
from pathlib import Path
import argparse
from typing import Optional, List, Dict, Any
import contextlib
import json

from config import Config

try:  # monitor module may not yet exist during partial development
    from monitor import TestFlightMonitor  # type: ignore
except Exception:  # pragma: no cover - fallback stub

    class TestFlightMonitor:  # type: ignore
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        async def __aenter__(self) -> "TestFlightMonitor":  # type: ignore
            return self

        async def __aexit__(self, *_exc: Any) -> bool:
            return False

        async def run_cycle(self) -> None:  # pragma: no cover
            return None

        async def check_multiple_apps(
            self, app_ids: List[str]
        ) -> List[Dict[str, Any]]:  # pragma: no cover
            return [{"app_id": a, "available": False} for a in app_ids]


class CLIApplication:
    """CLI with improved logging, signal handling, and resilience."""

    def __init__(self):
        self.monitor: Optional[TestFlightMonitor] = None
        self.running: bool = False
        self._stop_event: asyncio.Event | None = None
        self._logging_initialized = False
        # Logging init deferred until we know desired level (via CLI/env)
        self._defer_signal_setup = False
        self.logger = logging.getLogger(__name__)

    # ----------------------------- Logging ---------------------------------
    def setup_logging(
        self,
        level: Optional[str] = None,
        utc: bool = False,
        json_logs: bool = False,
    ) -> None:
        """Setup logging with rotation; idempotent.

        Level precedence: explicit arg > env TFM_LOG_LEVEL > default INFO.
        If json_logs True (or env TFM_LOG_JSON=1), use structured JSON lines.
        """
        if self._logging_initialized:
            if level:
                logging.getLogger().setLevel(level.upper())
            return
        from logging.handlers import RotatingFileHandler

        Path("logs").mkdir(exist_ok=True)

        file_handler = RotatingFileHandler(
            "logs/testflight_monitor.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
        )
        console_handler = logging.StreamHandler()

        class _UTCFormatter(logging.Formatter):
            converter = time.gmtime

        # Decide on formatter (plain vs JSON)
        json_env = os.getenv("TFM_LOG_JSON") in {"1", "true", "TRUE", "yes"}
        use_json = json_logs or json_env
        if use_json:

            class _JSONFormatter(logging.Formatter):  # noqa: D401 - simple
                def format(
                    self, record: logging.LogRecord
                ) -> str:  # type: ignore[override]
                    base = {
                        "ts": (
                            time.strftime(
                                "%Y-%m-%dT%H:%M:%SZ",
                                time.gmtime(record.created),
                            )
                            if utc
                            else time.strftime(
                                "%Y-%m-%dT%H:%M:%S",
                                time.localtime(record.created),
                            )
                        ),
                        "level": record.levelname,
                        "name": record.name,
                        "msg": record.getMessage(),
                    }
                    if record.exc_info:
                        base["exc_info"] = self.formatException(record.exc_info)
                    return json.dumps(base, ensure_ascii=False)

            formatter = _JSONFormatter()
        else:
            fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
            datefmt = "%Y-%m-%dT%H:%M:%SZ" if utc else None
            FormatterClass = _UTCFormatter if utc else logging.Formatter
            formatter = FormatterClass(fmt, datefmt=datefmt)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        root = logging.getLogger()
        # Avoid duplicate handlers if root already configured (e.g. tests)
        if not root.handlers:
            root.addHandler(file_handler)
            root.addHandler(console_handler)

        resolved_level = (level or os.getenv("TFM_LOG_LEVEL") or "INFO").upper()
        if resolved_level not in {
            "CRITICAL",
            "ERROR",
            "WARNING",
            "INFO",
            "DEBUG",
            "NOTSET",
        }:
            resolved_level = "INFO"
        root.setLevel(resolved_level)
        self._logging_initialized = True
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Logging initialized (level=%s, utc=%s)", resolved_level, utc)

    # ------------------------- Signal Handling -----------------------------
    def setup_signal_handlers(self) -> None:
        """Register signal handlers using the asyncio loop."""
        if sys.platform == "win32":  # add_signal_handler lacks SIGTERM
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Loop not ready yet; will attempt later
            self._defer_signal_setup = True
            return

        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, self.request_stop)
        self._defer_signal_setup = False

    def request_stop(self) -> None:
        if self.running:
            self.logger.info("Shutdown signal received; stopping...")
        self.running = False
        if self._stop_event is not None:
            self._stop_event.set()

    # ----------------------------- Run Loop --------------------------------
    async def _monitor_loop(self, config: Config) -> None:
        """Monitoring loop with backoff and fixed cadence."""
        assert self.monitor is not None
        interval = int(getattr(config, "check_interval_seconds", 60))
        backoff: float = 0.2 if interval <= 1 else 5.0
        max_backoff = 300.0
        self._stop_event = asyncio.Event()
        async with self.monitor:
            cycle = 0
            while self.running:
                cycle += 1
                cycle_start = asyncio.get_running_loop().time()
                try:
                    self.logger.debug("Starting cycle %d", cycle)
                    await self.monitor.run_cycle()
                    backoff = 0.2 if interval <= 1 else 5.0  # reset
                except asyncio.CancelledError:
                    raise
                except Exception as e:  # noqa: BLE001
                    self.logger.error(
                        "Cycle %d error (retry in %.2fs): %s",
                        cycle,
                        backoff,
                        e,
                        exc_info=True,
                    )
                    try:
                        await asyncio.wait_for(self._stop_event.wait(), timeout=backoff)
                    except asyncio.TimeoutError:
                        pass
                    backoff = min(backoff * 1.8, max_backoff)
                    continue

                elapsed = asyncio.get_running_loop().time() - cycle_start
                remaining = max(0.0, interval - elapsed)
                self.logger.debug(
                    "Cycle %d in %.2fs (sleep %.2fs)",
                    cycle,
                    elapsed,
                    remaining,
                )
                if remaining <= 0:
                    continue
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=remaining)
                except asyncio.TimeoutError:
                    pass

    async def run(self, config_path: Optional[str] = None) -> None:
        """Entry point to run continuous monitoring until stopped."""
        try:
            config = Config()
        except Exception as e:
            logging.getLogger(__name__).critical(
                "Configuration load failed: %s", e, exc_info=True
            )
            sys.exit(2)

        app_ids: List[str] = getattr(config, "app_ids", [])
        if not app_ids:
            self.logger.warning("No app IDs configured; exiting.")
            return

        if hasattr(config, "to_dict") and callable(getattr(config, "to_dict")):
            try:
                cfg_info: Any = config.to_dict()  # type: ignore[attr-defined]
                self.logger.info("Configuration loaded: %s", cfg_info)
            except Exception:  # pragma: no cover - defensive
                self.logger.debug("Config to_dict() failed", exc_info=True)

        self.monitor = TestFlightMonitor(config)
        self.running = True
        self.setup_signal_handlers()
        if self._defer_signal_setup:
            self.setup_signal_handlers()

        self.logger.info("TestFlight monitoring started")
        try:
            await self._monitor_loop(config)
        finally:
            self.logger.info("TestFlight monitoring stopped")

    # ---------------------------- Single Check -----------------------------
    async def run_single_check(self, config_path: Optional[str]) -> int:
        """Run a single availability check; return exit code."""
        try:
            config = Config()
        except Exception as e:
            print(f"✗ Configuration error: {e}")
            return 2

        app_ids: List[str] = getattr(config, "app_ids", [])
        if not app_ids:
            print("No app IDs configured.")
            return 3

        monitor = TestFlightMonitor(config)
        exit_code = 0
        async with monitor:
            results = await monitor.check_multiple_apps(app_ids)
            for result in results:
                status = "Available" if result.get("available") else "Not Available"
                if result.get("available"):
                    exit_code = 0  # explicit for clarity
                print(f"{result['app_id']}: {status}")
        return exit_code


def main():
    """CLI entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="TestFlight Monitor")
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument(
        "--check",
        "--once",
        action="store_true",
        help="Run single check and exit",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration and exit",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    parser.add_argument(
        "--log-utc",
        action="store_true",
        help="Log timestamps in UTC (ISO 8601)",
    )
    parser.add_argument(
        "--log-json",
        action="store_true",
        help="Emit structured JSON log lines",
    )

    args = parser.parse_args()

    if args.validate:
        try:
            config = Config()
            print("✓ Configuration is valid")
            print(f"Monitoring {len(config.app_ids)} apps:")
            for app_id in config.app_ids:
                print(f"  - {app_id}")
            return
        except Exception as e:
            print(f"✗ Configuration error: {e}")
            sys.exit(2)

    app = CLIApplication()
    app.setup_logging(
        level=args.log_level,
        utc=args.log_utc,
        json_logs=args.log_json,
    )

    if args.check:
        exit_code = asyncio.run(app.run_single_check(config_path=args.config))
        sys.exit(exit_code)

    # Continuous monitoring
    try:
        asyncio.run(app.run(config_path=args.config))
    except KeyboardInterrupt:
        # Already handled via signal; fallback for limited platforms
        pass


if __name__ == "__main__":  # pragma: no cover
    main()
