import logging
import os
import apprise
from typing import Optional, Any
from datetime import datetime

try:
    from config import Config  # type: ignore
except Exception:  # pragma: no cover
    Config = Any  # fallback for typing

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manages notifications via Apprise with per-app cooldown.

    Default cooldown 600 seconds; override with env var TFM_NOTIFY_COOLDOWN.
    """

    def __init__(self, config: Config):  # type: ignore[name-defined]
        self.config = config
        self.apprise_obj = apprise.Apprise()
        self.last_notification: dict[str, datetime] = {}
        # Cooldown seconds per app (default 600); allow override via env
        try:
            self.cooldown = int(os.getenv("TFM_NOTIFY_COOLDOWN", "600"))
        except Exception:  # pragma: no cover
            self.cooldown = 600
        self._setup_notifications()

    def _setup_notifications(self) -> None:
        """Setup Apprise notification endpoints."""
        added_count = 0

        # Add Discord webhook if configured
        if self.config.notifications.discord_webhook_url:
            # Extract webhook ID and token from Discord URL
            webhook_url = self.config.notifications.discord_webhook_url
            if "discord.com/api/webhooks/" in webhook_url:
                webhook_parts = webhook_url.split("/")[-2:]
                apprise_url = f"discord://{webhook_parts[0]}/{webhook_parts[1]}"
                if self.apprise_obj.add(apprise_url):
                    added_count += 1
                    logger.info("Discord notification configured")

        # Add Slack webhook if configured
        if self.config.notifications.slack_webhook_url:
            if self.apprise_obj.add(self.config.notifications.slack_webhook_url):
                added_count += 1
                logger.info("Slack notification configured")

        # Add email if configured
        if self.config.notifications.email_smtp_server:
            email_url = (
                f"mailto://{self.config.notifications.email_username}:"
                f"{self.config.notifications.email_password}@"
                f"{self.config.notifications.email_smtp_server}:"
                f"{self.config.notifications.email_smtp_port}"
            )

            # Add recipients
            if self.config.notifications.email_recipients:
                recipients = ",".join(self.config.notifications.email_recipients)
                email_url += f"?to={recipients}"

            if self.apprise_obj.add(email_url):
                added_count += 1
                logger.info("Email notification configured")

        # Add Pushover last (independent)
        if (
            self.config.notifications.pushover_user_key
            and self.config.notifications.pushover_api_token
        ):
            pu = self.config.notifications
            base = f"pushover://{pu.pushover_user_key}@" f"{pu.pushover_api_token}/"
            params: list[str] = []
            if pu.pushover_priority:
                params.append(f"priority={pu.pushover_priority}")
            if pu.pushover_sound:
                params.append(f"sound={pu.pushover_sound}")
            if params:
                base = base + "?" + "&".join(params)
            if self.apprise_obj.add(base):
                added_count += 1
                logger.info("Pushover notification configured")

        # Final count log
        logger.info(f"Configured {added_count} notification services")

    async def send_notification(
        self, title: str, message: str, app_id: Optional[str] = None
    ) -> None:
        """Send notification through all configured Apprise services."""
        # Rate limiting
        if app_id:
            now = datetime.now()
            last_sent = self.last_notification.get(app_id)
            if last_sent and (now - last_sent).total_seconds() < self.cooldown:
                logger.info(f"Skipping notification for {app_id} - rate limited")
                return
            self.last_notification[app_id] = now

        try:
            # Send notification through all configured services
            success = self.apprise_obj.notify(  # type: ignore[call-arg]
                title=title,
                body=message,
                notify_type=apprise.NotifyType.SUCCESS,  # type: ignore[attr-defined]
            )

            if success:
                logger.info(f"Notification sent successfully: {title}")
            else:
                logger.error(f"Failed to send notification: {title}")

        except Exception as e:
            logger.error(f"Error sending notification: {e}")
