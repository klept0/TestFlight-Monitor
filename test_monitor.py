import asyncio
from config import Config
import os
from monitor import TestFlightMonitor
from main import CLIApplication


def test_monitor_cycle_basic() -> None:
    cfg = Config(app_ids=["FAKECODE"])

    async def run():
        monitor = TestFlightMonitor(cfg)
        # Patch network call to avoid external dependency

        async def fake_fetch(app_id: str) -> bool:
            return False

        monitor._fetch_availability = fake_fetch  # type: ignore
        async with monitor:
            results = await monitor.check_multiple_apps(cfg.app_ids)
        return results

    results = asyncio.run(run())
    assert len(results) == 1
    assert results[0]["app_id"] == cfg.app_ids[0]
    assert "available" in results[0]


def test_cli_single_check() -> None:
    cfg = Config(app_ids=["FAKECODE2"])

    async def run():
        app = CLIApplication()
        app.setup_logging(level="DEBUG")
        # Patch monitor fetch inside single check by subclass substitution
        import main as main_module

        orig_cls = main_module.TestFlightMonitor
        # Provide env var so internal Config() validation passes
        prev = os.environ.get("TESTFLIGHT_APP_IDS")
        os.environ["TESTFLIGHT_APP_IDS"] = ",".join(cfg.app_ids)

        class FakeMonitor(orig_cls):  # type: ignore
            async def check_multiple_apps(self, app_ids):  # type: ignore
                return [{"app_id": a, "available": False} for a in app_ids]

        # Swap symbol in imported module
        main_module.TestFlightMonitor = FakeMonitor  # type: ignore
        try:
            code = await app.run_single_check(config_path=None)
        finally:
            main_module.TestFlightMonitor = orig_cls  # type: ignore
            if prev is None:
                del os.environ["TESTFLIGHT_APP_IDS"]
            else:
                os.environ["TESTFLIGHT_APP_IDS"] = prev
        return code

    exit_code = asyncio.run(run())
    assert exit_code == 0


def test_interpret_page_heuristics() -> None:
    cfg = Config(app_ids=["FAKE"])
    monitor = TestFlightMonitor(cfg)
    positive = "<html><body><h1>Join the beta now</h1></body></html>"
    negative = "<div>This beta is full</div>"
    ambiguous = "<p>Welcome tester portal</p>"
    assert monitor.interpret_page(positive) is True
    assert monitor.interpret_page(negative) is False
    assert monitor.interpret_page(ambiguous) is False


def test_cli_version_flag(capsys=None) -> None:  # type: ignore[no-untyped-def]
    import sys
    import main as main_module

    argv_backup = sys.argv[:]  # keep copy
    sys.argv = ["main.py", "--version"]
    try:
        main_module.main()
    finally:
        sys.argv = argv_backup
    if capsys is not None:  # pragma: no branch
        captured = capsys.readouterr().out.strip()  # type: ignore[attr-defined]  # noqa: E501
        assert captured


def test_monitor_backoff_behavior() -> None:
    """Ensure monitor loop retries after failures and eventually succeeds.

    Uses a stub monitor that fails twice then succeeds. We stop the loop
    after success to avoid long runtime.
    """
    import asyncio
    from main import CLIApplication

    class StubMonitor:
        def __init__(self):
            self.attempts = 0
            self.entered = False

        async def __aenter__(self):
            self.entered = True
            return self

        async def __aexit__(self, *exc):
            return False

        async def run_cycle(self):
            self.attempts += 1
            if self.attempts < 3:
                raise RuntimeError("fail")
            # succeed silently on 3rd attempt

    class StubConfig:
        check_interval_seconds = 1
        app_ids = ["FAKE"]

    async def run():
        app = CLIApplication()
        app.setup_logging(level="ERROR")
        app.monitor = StubMonitor()  # type: ignore
        app.running = True
        # Run loop concurrently
        task = asyncio.create_task(
            app._monitor_loop(StubConfig())  # type: ignore[arg-type]
        )
        # Wait until 3 attempts or timeout
        for _ in range(60):
            if app.monitor.attempts >= 3:  # type: ignore[attr-defined]
                app.request_stop()
                break
            await asyncio.sleep(0.05)
        await asyncio.wait_for(task, timeout=5)
        return app.monitor.attempts  # type: ignore[attr-defined]

    attempts = asyncio.run(run())
    assert attempts >= 3
