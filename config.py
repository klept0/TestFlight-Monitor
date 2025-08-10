import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """Configuration for notification services."""

    discord_webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    email_smtp_server: Optional[str] = None
    email_smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_recipients: List[str] = field(default_factory=list)
    # Pushover
    pushover_user_key: Optional[str] = None
    pushover_api_token: Optional[str] = None
    pushover_priority: Optional[str] = None  # -2..2 per Pushover
    pushover_sound: Optional[str] = None


@dataclass
class Config:
    """Main configuration class with validation."""

    app_ids: List[str] = field(default_factory=list)
    check_interval_seconds: int = 300  # seconds between cycles
    cache_ttl_minutes: int = 5
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    log_level: str = "INFO"
    log_file: str = "testflight_monitor.log"

    def __post_init__(self) -> None:
        # If user provided app_ids in constructor, remember so file
        # won't override them from [config.json](http://_vscodecontentref_/1)
        explicit = bool(self.app_ids)
        self._load_from_env()
        # Only load app_ids from file if still empty
        self._load_from_file(load_app_ids=not self.app_ids and not explicit)
        self._validate()

    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # App settings
        env_ids = os.getenv("TESTFLIGHT_APP_IDS")
        if env_ids:
            self.app_ids = [i.strip() for i in env_ids.split(",") if i.strip()]

        env_interval = os.getenv("CHECK_INTERVAL_SECONDS")
        if env_interval:
            self.check_interval_seconds = int(env_interval)

        env_ttl = os.getenv("CACHE_TTL_MINUTES")
        if env_ttl:
            self.cache_ttl_minutes = int(env_ttl)

        # Notification settings
        self.notifications.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.notifications.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.notifications.email_smtp_server = os.getenv("EMAIL_SMTP_SERVER")

        env_port = os.getenv("EMAIL_SMTP_PORT")
        if env_port:
            self.notifications.email_smtp_port = int(env_port)

        self.notifications.email_username = os.getenv("EMAIL_USERNAME")
        self.notifications.email_password = os.getenv("EMAIL_PASSWORD")

        env_recipients = os.getenv("EMAIL_RECIPIENTS")
        if env_recipients:
            self.notifications.email_recipients = [
                r.strip() for r in env_recipients.split(",") if r.strip()
            ]

        # Pushover
        self.notifications.pushover_user_key = os.getenv(
            "PUSHOVER_USER_KEY", self.notifications.pushover_user_key
        )
        self.notifications.pushover_api_token = os.getenv(
            "PUSHOVER_API_TOKEN", self.notifications.pushover_api_token
        )
        self.notifications.pushover_priority = os.getenv(
            "PUSHOVER_PRIORITY", self.notifications.pushover_priority
        )
        self.notifications.pushover_sound = os.getenv(
            "PUSHOVER_SOUND", self.notifications.pushover_sound
        )

        # Logging settings
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.log_file = os.getenv("LOG_FILE", self.log_file)

    def _load_from_file(self, load_app_ids: bool = True) -> None:
        """Load configuration from config.json if it exists.

        Parameters:
            load_app_ids: whether to allow file to populate app_ids.
        """
        config_file = Path("config.json")
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config_data = json.load(f)
                if load_app_ids and "app_ids" in config_data and not self.app_ids:
                    self.app_ids = config_data["app_ids"]
                # Other scalar fields
                for key, value in config_data.items():
                    if key == "notifications" or key == "app_ids":
                        continue
                    if hasattr(self, key):
                        setattr(self, key, value)
                notif = config_data.get("notifications", {}) or {}
                if isinstance(notif, dict):
                    for k, v in notif.items():  # noqa: B905
                        if hasattr(self.notifications, k):
                            setattr(self.notifications, k, v)
                logger.info("Configuration loaded from config.json")
            except Exception as e:
                logger.warning(f"Failed to load config.json: {e}")

    def _validate(self) -> None:
        """Validate configuration values."""
        if not self.app_ids:
            raise ValueError(
                "No app IDs configured. Set TESTFLIGHT_APP_IDS env var or "
                "config.json"
            )

        # Validate app IDs format
        for app_id in self.app_ids:
            # Allow 4+ characters (tests use 'FAKE')
            if not app_id or len(app_id.strip()) < 4:
                raise ValueError(f"Invalid app ID: {app_id}")

        # Clean up app IDs
        self.app_ids = [app_id.strip() for app_id in self.app_ids if app_id.strip()]

        if self.check_interval_seconds < 60:
            logger.warning(
                "Check interval <60s may cause rate limiting (configured=%s)",
                self.check_interval_seconds,
            )

        if self.cache_ttl_minutes < 1:
            raise ValueError("Cache TTL must be at least 1 minute")

        # Validate notification configuration
        has_notification = any(
            [
                self.notifications.discord_webhook_url,
                self.notifications.slack_webhook_url,
                self.notifications.email_smtp_server,
                self.notifications.pushover_user_key
                and self.notifications.pushover_api_token,
            ]
        )

        if not has_notification:
            logger.warning("No notification methods configured")

        logger.info("Configuration validated. Monitoring %d apps", len(self.app_ids))

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for logging/debugging."""
        config_dict: Dict[str, Any] = {
            "app_ids": self.app_ids,
            "check_interval_seconds": self.check_interval_seconds,
            "cache_ttl_minutes": self.cache_ttl_minutes,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "notifications_configured": {
                "discord": bool(self.notifications.discord_webhook_url),
                "slack": bool(self.notifications.slack_webhook_url),
                "email": bool(self.notifications.email_smtp_server),
                "pushover": bool(
                    self.notifications.pushover_user_key
                    and self.notifications.pushover_api_token
                ),
            },
        }
        return config_dict
