import logging
from typing import List, Dict, Any, Optional
import aiohttp
from datetime import datetime, timedelta

from config import Config
from notifications import NotificationManager

logger = logging.getLogger(__name__)

__all__ = ["TestFlightMonitor"]

class TestFlightMonitor:
    """Monitor TestFlight app codes for availability.

    This implementation performs HTTP GET requests to the public TestFlight
    landing page for each app code (placeholder logic). Real scraping/parsing
    should inspect the response content structure and decide availability.
    """

    def __init__(self, config: Config):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self.notification_manager = NotificationManager(config)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = timedelta(minutes=config.cache_ttl_minutes)

    async def __aenter__(self) -> "TestFlightMonitor":
        timeout = aiohttp.ClientTimeout(total=30)
        self._session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, *exc_info) -> None:
        if self._session:
            await self._session.close()
        self._session = None

    async def run_cycle(self) -> None:
        """Run a single monitoring cycle over all configured app IDs."""
        await self.check_multiple_apps(self.config.app_ids)

    async def check_multiple_apps(
        self, app_ids: List[str]
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for app_id in app_ids:
            result = await self._check_single_app(app_id)
            results.append(result)
        return results

    async def _check_single_app(self, app_id: str) -> Dict[str, Any]:
    now = datetime.now()
        # Cache check
        cached = self._cache.get(app_id)
        if cached and (now - cached["timestamp"]) < self._cache_ttl:
            return cached["data"]

        available = await self._fetch_availability(app_id)
        data = {
            "app_id": app_id,
            "available": available,
            "checked_at": now.isoformat(),
        }
        self._cache[app_id] = {"timestamp": now, "data": data}

        if available:
            await self.notification_manager.send_notification(
                title=f"TestFlight Slot Available: {app_id}",
                message=f"An open slot was detected for {app_id}",
                app_id=app_id,
            )
        return data

    async def _fetch_availability(self, app_id: str) -> bool:
        """Placeholder availability check.

        Fetches the public TestFlight join page and interprets content.
        Heuristic categories:
        - Available: phrases like "Join the beta" or button markers
        - Full: phrases like "This beta is full" / "The beta is currently full"
        - Expired/Not Available: various error phrases
        - Unknown: default to not available (False) to avoid false positives
        """
        url = f"https://testflight.apple.com/join/{app_id}"
        try:
            if not self._session:
                raise RuntimeError("Session not initialized")
            async with self._session.get(
                url, headers={"User-Agent": "Mozilla/5.0"}
            ) as resp:
                if resp.status != 200:
                    logger.debug("App %s page status %s", app_id, resp.status)
                    return False
                text = await resp.text()
                available = self._interpret_page(text)
                if available:
                    logger.info(
                        "Potential availability detected for %s", app_id
                    )
                return available
        except Exception as e:  # noqa: BLE001
            logger.warning("Fetch failed for %s: %s", app_id, e)
            return False

    # -------- Heuristic Parser (exposed for testing) --------------------
    def _interpret_page(self, html: str) -> bool:
        """Return True if page content strongly indicates open slots.

        Conservative: only return True on positive signals; ambiguous text
        yields False. This function is pure & testable.
        """
        lowered = html.lower()
        positive_markers = [
            "join the beta",  # common CTA
            "accepting testers",  # hypothetical phrasing
            "beta signup",  # general
            "open beta",  # general
        ]
        negative_markers = [
            "beta is full",
            "currently full",
            "this beta is full",
            "no longer accepting new testers",
            "this beta isn't accepting",
            "beta has ended",
            "not available",
            "unavailable",
        ]
        if any(n in lowered for n in negative_markers):
            return False
        if any(p in lowered for p in positive_markers):
            return True
        return False

    # Public wrapper for tests / external diagnostics
    def interpret_page(self, html: str) -> bool:
        """Public wrapper exposing availability heuristic."""
        return self._interpret_page(html)
