import os
import logging
import requests
import logging
import requests
from enum import Enum
from typing import List
from typing import Optional
from datetime import timedelta, datetime
from dataclasses import dataclass, field


# Configure logger
logger = logging.getLogger(__name__)

class DataSource(Enum):
    """Available data sources for train information."""
    SIMULATE = "simulate"
    RAPIDAPI = "rapidapi"
    ERAIL = "erail"

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
    REQUEST_TIMEOUT = 15
    MAX_RETRIES = 3
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration settings."""
        if cls.DATA_SOURCE == DataSource.RAPIDAPI and not cls.RAPIDAPI_KEY:
            logger.error("RapidAPI key not configured")
            return False
        return True
    
@dataclass
class TrainETA:
    """Train with estimated time of arrival."""
    train_no: str
    name: str
    eta_at_station: datetime
    eta_at_crossing: datetime
    source: str
    delay_min: Optional[int] = None
    speed_kmph: Optional[float] = None
    
    def minutes_to_crossing(self) -> int:
        """Calculate minutes until train reaches crossing."""
        delta = self.eta_at_crossing - datetime.now()
        return max(0, int(delta.total_seconds() // 60))

class TrainDataFetcher:
    """Base class for train data fetchers."""
    
    def fetch(self, station_code: str, hours: int) -> List[TrainETA]:
        """Fetch train data. Must be implemented by subclasses."""
        raise NotImplementedError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def now() -> datetime:
    """Get current datetime."""
    return datetime.now()

def minutes(m: int) -> timedelta:
    """Convert minutes to timedelta."""
    return timedelta(minutes=m)

def km_to_minutes(distance_km: float, speed_kmph: float) -> float:
    """Convert distance and speed to travel time in minutes."""
    if speed_kmph <= 0:
        speed_kmph = Config.MIN_SPEED_KMPH
    return (distance_km / speed_kmph) * 60

def fmt(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%H:%M")

def parse_time_string(time_str: str, base: datetime) -> Optional[datetime]:
    """
    Parse a HH:MM string into a datetime object relative to base.
    Rolls over to the next day if the time has already passed today.
    """
    try:
        if not time_str or ":" not in time_str:
            return None

        hour, minute = map(int, time_str.split(":"))

        # Build datetime with today's date
        eta = datetime(
            year=base.year,
            month=base.month,
            day=base.day,
            hour=hour,
            minute=minute
        )

        # If that time has already passed today, assume it's tomorrow
        if eta < base:
            eta += timedelta(days=1)

        return eta
    except Exception as e:
        logger.debug(f"Failed to parse time string {time_str}: {e}")
        return None



logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ERAIL_URL = "https://erail.in/rail/getTrains.aspx"
params = {
                "Station_From": "VN",
                "Station_To": "VN",
                "DataSource": 0,
                "Language": 0,
                "Cache": "true"
            }
res = requests.get(ERAIL_URL, params=params)

def _parse_erail_response(raw_text: str, station_code: str, hours: int) -> List[TrainETA]:
        """Parse Erail response text."""
        trains = []
        base = datetime.now()
        eta_station = base + timedelta(minutes=30)
        
        if not raw_text or "^" not in raw_text:
            logger.warning("Empty or invalid Erail response")
            return trains
        
        for record in raw_text.split("^"):
            parts = record.split("~")
            if len(parts) < 10:
                continue
            
            try:
                train_no = parts[0].strip()
                name = parts[1].strip()
                
                # Find arrival time for the station
                arr_time = None
                if station_code in parts:
                    idx = parts.index(station_code)
                    if len(parts) > idx + 1:
                        arr_time = parts[idx + 1]

                        if not arr_time:
                            continue

                
                # Parse arrival time
                eta_station = parse_time_string(arr_time, base)
                if not eta_station:
                    eta_station = base + minutes(30)  # Default fallback
                
                # Calculate crossing ETA
                offset_min = km_to_minutes(
                    Config.DIST_KM_FROM_STATION, 
                    Config.AVG_SPEED_KMPH
                )
                eta_crossing = eta_station - minutes(int(offset_min))
                
                # Only include trains within the time window
                if not (base <= eta_crossing <= base + timedelta(hours=hours)):
                    continue
                
                logger.debug(f"Trying to parse arrival time: {arr_time}")
                eta_station = parse_time_string(arr_time, base)
                trains.append(TrainETA(
                    train_no=train_no,
                    name=name,
                    eta_at_station=eta_station,
                    eta_at_crossing=eta_crossing,
                    source="erail",
                    delay_min=None,
                    speed_kmph=Config.AVG_SPEED_KMPH
                ))
                
            except (ValueError, IndexError) as e:
                logger.debug(f"Failed to parse train record: {e}")
                continue
        
        return trains
trains = _parse_erail_response(res.text, 'VN', 2)

for train in trains:
    print(f"Train {train.train_no}: {train.name}")
    print(f"  ETA at station: {train.eta_at_station}")
    print(f"  ETA at crossing: {train.eta_at_crossing}")
    print(f"  Minutes to crossing: {train.minutes_to_crossing()}")
    print()