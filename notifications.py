import logging
import apprise
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manages notifications using Apprise library."""
    
    def __init__(self, config):
        self.config = config
        self.apprise_obj = apprise.Apprise()
        self.last_notification = {}
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
            email_url = (f"mailto://{self.config.notifications.email_username}:"
                        f"{self.config.notifications.email_password}@"
                        f"{self.config.notifications.email_smtp_server}:"
                        f"{self.config.notifications.email_smtp_port}")
            
            # Add recipients
            if self.config.notifications.email_recipients:
                recipients = ",".join(self.config.notifications.email_recipients)
                email_url += f"?to={recipients}"
            
            if self.apprise_obj.add(email_url):
                added_count += 1
                logger.info("Email notification configured")
        
        logger.info(f"Configured {added_count} notification services")
    
    async def send_notification(self, title: str, message: str, app_id: Optional[str] = None) -> None:
        """Send notification through all configured Apprise services."""
        # Rate limiting
        if app_id:
            now = datetime.now()
            last_sent = self.last_notification.get(app_id)
            if last_sent and (now - last_sent).seconds < 600:  # 10 minutes
                logger.info(f"Skipping notification for {app_id} - rate limited")
                return
            self.last_notification[app_id] = now
        
        try:
            # Send notification through all configured services
            success = self.apprise_obj.notify(
                title=title,
                body=message,
                notify_type=apprise.NotifyType.SUCCESS
            )
            
            if success:
                logger.info(f"Notification sent successfully: {title}")
            else:
                logger.error(f"Failed to send notification: {title}")
                
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
