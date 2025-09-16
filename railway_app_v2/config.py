from .models import DataSource
import os
import logging

# Configure logger
logger = logging.getLogger(__name__)
class Config:
    """Centralized configuration management."""
    
    # Data source selection
    DATA_SOURCE = DataSource.ERAIL  # Change to RAPIDAPI or SIMULATE as needed
    
    # Station and crossing details
    STATION_CODE = "VN"  # Nearest station to level crossing
    WINDOW_HOURS = 2  # Look-ahead window for trains
    DIST_KM_FROM_STATION = 1.0  # Distance of crossing from station
    
    # Gate timing parameters
    PRE_CLOSE_BUFFER_MIN = 5  # Minutes before train arrival to close gate
    POST_OPEN_BUFFER_MIN = 3  # Minutes after train passes to open gate
    PASS_DURATION_MIN = 2  # Time for train to pass crossing
    
    # Train speed assumptions
    MIN_SPEED_KMPH = 30  # Minimum speed near station
    AVG_SPEED_KMPH = 50  # Average speed for calculations
    MAX_SPEED_KMPH = 100  # Maximum speed for validation
    
    # API Configuration
    RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
    RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "irctc1.p.rapidapi.com")
    
    # Polling configuration
    POLL_INTERVAL_SECS = 60
    REQUEST_TIMEOUT = 30  # Increased timeout for slower connections
    MAX_RETRIES = 5  # Increased retries
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration settings."""
        if cls.DATA_SOURCE == DataSource.RAPIDAPI and not cls.RAPIDAPI_KEY:
            logger.error("RapidAPI key not configured")
            return False
        return True