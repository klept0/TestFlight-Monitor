import asyncio
import logging
import signal
import sys
from pathlib import Path
import argparse
from datetime import datetime
from typing import Optional

from config import Config
from monitor import TestFlightMonitor

class CLIApplication:
    """Robust CLI application with proper signal handling and logging."""
    
    def __init__(self):
        self.monitor: Optional[TestFlightMonitor] = None
        self.running = False
        self.setup_logging()
        self.setup_signal_handlers()
    
    def setup_logging(self):
        """Setup comprehensive logging with rotation."""
        from logging.handlers import RotatingFileHandler
        
        # Create logs directory
        Path("logs").mkdir(exist_ok=True)
        
        # Setup rotating file handler
        file_handler = RotatingFileHandler(
            "logs/testflight_monitor.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        self.logger = logging.getLogger(__name__)
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers."""
        if sys.platform != "win32":
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    async def run(self, config_path: Optional[str] = None) -> None:
        """Run the monitoring application."""
        try:
            # Load configuration
            config = Config(config_path=config_path)
            self.logger.info(f"Configuration loaded: {config.to_dict()}")
            
            # Create monitor
            self.monitor = TestFlightMonitor(config)
            self.running = True
            
            self.logger.info("Starting TestFlight monitoring...")
            
            async with self.monitor:
                while self.running:
                    try:
                        await self.monitor.run_cycle()
                        
                        # Check for shutdown every second during sleep
                        for _ in range(config.check_interval_seconds):
                            if not self.running:
                                break
                            await asyncio.sleep(1)
                            
                    except KeyboardInterrupt:
                        self.logger.info("Interrupted by user")
                        break
                    except Exception as e:
                        self.logger.error(f"Error in monitoring cycle: {e}")
                        await asyncio.sleep(60)  # Wait before retry
            
            self.logger.info("TestFlight monitoring stopped")
            
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            sys.exit(1)

def main():
    """CLI entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="TestFlight Monitor")
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--gui", action="store_true", help="Launch GUI interface")
    parser.add_argument("--check", action="store_true", help="Run single check and exit")
    parser.add_argument("--validate", action="store_true", help="Validate configuration and exit")
    
    args = parser.parse_args()
    
    if args.gui:
        from gui import TestFlightGUI
        gui = TestFlightGUI()
        gui.run()
    elif args.validate:
        try:
            config = Config(config_path=args.config)
            print("✓ Configuration is valid")
            print(f"Monitoring {len(config.app_ids)} apps:")
            for app_id in config.app_ids:
                print(f"  - {app_id}")
        except Exception as e:
            print(f"✗ Configuration error: {e}")
            sys.exit(1)
    elif args.check:
        # Single check mode
        async def single_check():
            config = Config(config_path=args.config)
            monitor = TestFlightMonitor(config)
            async with monitor:
                results = await monitor.check_multiple_apps(config.app_ids)
                for result in results:
                    status = "Available" if result.get('available') else "Not Available"
                    print(f"{result['app_id']}: {status}")
        
        asyncio.run(single_check())
    else:
        # Standard monitoring mode
        app = CLIApplication()
        asyncio.run(app.run(config_path=args.config))

if __name__ == "__main__":
    main()
