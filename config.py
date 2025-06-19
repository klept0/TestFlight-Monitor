import os
from typing import List, Optional
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

@dataclass
class Config:
    """Main configuration class with validation."""
    
    # App monitoring settings
    app_ids: List[str] = field(default_factory=list)
    check_interval_seconds: int = 300  # 5 minutes
    cache_ttl_minutes: int = 5
    
    # Notification settings
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    
    # Logging settings
    log_level: str = "INFO"
    log_file: str = "testflight_monitor.log"
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._load_from_env()
        self._load_from_file()
        self._validate()
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # App settings
        if os.getenv('TESTFLIGHT_APP_IDS'):
            self.app_ids = os.getenv('TESTFLIGHT_APP_IDS').split(',')
        
        if os.getenv('CHECK_INTERVAL_SECONDS'):
            self.check_interval_seconds = int(os.getenv('CHECK_INTERVAL_SECONDS'))
        
        if os.getenv('CACHE_TTL_MINUTES'):
            self.cache_ttl_minutes = int(os.getenv('CACHE_TTL_MINUTES'))
        
        # Notification settings
        self.notifications.discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.notifications.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        self.notifications.email_smtp_server = os.getenv('EMAIL_SMTP_SERVER')
        
        if os.getenv('EMAIL_SMTP_PORT'):
            self.notifications.email_smtp_port = int(os.getenv('EMAIL_SMTP_PORT'))
        
        self.notifications.email_username = os.getenv('EMAIL_USERNAME')
        self.notifications.email_password = os.getenv('EMAIL_PASSWORD')
        
        if os.getenv('EMAIL_RECIPIENTS'):
            self.notifications.email_recipients = os.getenv('EMAIL_RECIPIENTS').split(',')
        
        # Logging settings
        self.log_level = os.getenv('LOG_LEVEL', self.log_level)
        self.log_file = os.getenv('LOG_FILE', self.log_file)
    
    def _load_from_file(self) -> None:
        """Load configuration from config.json if it exists."""
        config_file = Path('config.json')
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Update app_ids if not set from env
                if not self.app_ids and 'app_ids' in config_data:
                    self.app_ids = config_data['app_ids']
                
                # Update other settings
                for key, value in config_data.items():
                    if hasattr(self, key) and key != 'notifications':
                        setattr(self, key, value)
                
                # Update notification settings
                if 'notifications' in config_data:
                    notif_data = config_data['notifications']
                    for key, value in notif_data.items():
                        if hasattr(self.notifications, key):
                            setattr(self.notifications, key, value)
                
                logger.info("Configuration loaded from config.json")
                
            except Exception as e:
                logger.warning(f"Failed to load config.json: {e}")
    
    def _validate(self) -> None:
        """Validate configuration values."""
        if not self.app_ids:
            raise ValueError("No app IDs configured. Set TESTFLIGHT_APP_IDS environment variable or config.json")
        
        # Validate app IDs format
        for app_id in self.app_ids:
            if not app_id or len(app_id.strip()) < 5:
                raise ValueError(f"Invalid app ID: {app_id}")
        
        # Clean up app IDs
        self.app_ids = [app_id.strip() for app_id in self.app_ids if app_id.strip()]
        
        if self.check_interval_seconds < 60:
            logger.warning("Check interval is less than 60 seconds, this may cause rate limiting")
        
        if self.cache_ttl_minutes < 1:
            raise ValueError("Cache TTL must be at least 1 minute")
        
        # Validate notification configuration
        has_notification = any([
            self.notifications.discord_webhook_url,
            self.notifications.slack_webhook_url,
            self.notifications.email_smtp_server
        ])
        
        if not has_notification:
            logger.warning("No notification methods configured")
        
        logger.info(f"Configuration validated. Monitoring {len(self.app_ids)} apps")
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary for logging/debugging."""
        config_dict = {
            'app_ids': self.app_ids,
            'check_interval_seconds': self.check_interval_seconds,
            'cache_ttl_minutes': self.cache_ttl_minutes,
            'log_level': self.log_level,
            'log_file': self.log_file,
            'notifications_configured': {
                'discord': bool(self.notifications.discord_webhook_url),
                'slack': bool(self.notifications.slack_webhook_url),
                'email': bool(self.notifications.email_smtp_server)
            }
        }
        return config_dict
