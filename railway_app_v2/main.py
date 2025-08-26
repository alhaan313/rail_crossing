import time
import logging
from typing import List
from datetime import datetime

from .models import TrainETA
from .config import Config, DataSource

from .fetchers.base import TrainDataFetcher
from .fetchers.simulation import SimulationFetcher
from .fetchers.rapidapi import RapidAPIFetcher
from .fetchers.erail import ErailFetcher

logger = logging.getLogger(__name__)

class RailwayCrossingApp:
    """Main application class."""
    
    def __init__(self):
        self.fetcher = self._get_fetcher()
    
    def _get_fetcher(self) -> TrainDataFetcher:
        if Config.DATA_SOURCE == DataSource.SIMULATE:
            logger.info("Using simulated data")
            return SimulationFetcher()
        elif Config.DATA_SOURCE == DataSource.RAPIDAPI:
            logger.info("Using RapidAPI data source")
            return RapidAPIFetcher()
        elif Config.DATA_SOURCE == DataSource.ERAIL:
            logger.info("Using Erail data source")
            return ErailFetcher()
        else:
            logger.warning("Unknown data source, falling back to simulation")
            return SimulationFetcher()
    
    def fetch_trains(self) -> List[TrainETA]:
        for attempt in range(Config.MAX_RETRIES):
            try:
                trains = self.fetcher.fetch(Config.STATION_CODE, Config.WINDOW_HOURS)
                current_time = datetime.now()
                valid_trains = [t for t in trains if t.eta_at_crossing >= current_time]
                logger.info(f"Fetched {len(valid_trains)} upcoming trains")
                return valid_trains   # ✅ FIX
            except Exception as e:
                logger.error(f"Fetch attempt {attempt + 1} failed: {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
        logger.error("All fetch attempts failed, returning empty list")
        return []
    
    def run_once(self):
        try:
            trains = self.fetch_trains()
            for t in trains:
                print(f"{t.train_no} {t.name} ETA at crossing: {t.eta_at_crossing}")
        except Exception as e:
            logger.error(f"Error in run cycle: {e}")
            print(f"\nError updating status: {e}")
    
    def run_loop(self):
        logger.info("Starting continuous monitoring mode")
        print(f"\n🔄 Monitoring mode: Updates every {Config.POLL_INTERVAL_SECS} seconds")
        print("Press Ctrl+C to stop\n")
        try:
            while True:
                self.run_once()
                time.sleep(Config.POLL_INTERVAL_SECS)
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped by user")
            logger.info("Application stopped by user")

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    if not Config.validate():
        print("Configuration validation failed. Please check settings.")
        return 1
    
    app = RailwayCrossingApp()

    import sys
    if "--loop" in sys.argv or "-l" in sys.argv:
        app.run_loop()
    else:
        app.run_once()
        print("\nTip: Run with --loop or -l flag for continuous monitoring")
    return 0

if __name__ == "__main__":
    exit(main())
