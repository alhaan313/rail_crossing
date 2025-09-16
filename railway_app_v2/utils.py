import math
import logging
from typing import Optional
from datetime import datetime, timedelta
import pytz

from railway_app_v2.config import Config 

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def now() -> datetime:
    """Get current datetime in IST."""
    return datetime.now(pytz.timezone('Asia/Kolkata'))

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
    Ensures timezone awareness.
    """
    try:
        if not time_str or ":" not in time_str:
            return None

        hour, minute = map(int, time_str.split(":"))

        # Build datetime with today's date in IST
        ist = pytz.timezone('Asia/Kolkata')
        eta = ist.localize(datetime(
            year=base.year,
            month=base.month,
            day=base.day,
            hour=hour,
            minute=minute
        ))

        # If that time has already passed today, assume it's tomorrow
        if eta < base:
            eta += timedelta(days=1)

        return eta
    except Exception as e:
        logger.debug(f"Failed to parse time string {time_str}: {e}")
        return None

def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def dedupe_by_proximity(nodes, threshold_m=35):
    reps = []
    threshold_km = threshold_m / 1000.0
    for n in nodes:
        found_cluster = False
        for r in reps:
            d = haversine_km(n["lon"], n["lat"], r["lon"], r["lat"])
            if d <= threshold_km:
                if (not r.get("name_tag")) and n.get("name_tag"):
                    r.update(n)
                found_cluster = True
                break
        if not found_cluster:
            reps.append(dict(n))
    return reps
