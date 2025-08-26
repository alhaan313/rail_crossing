
import requests
import logging
from typing import List, Dict, Any

from .base import TrainDataFetcher
from ..models import TrainETA
from ..config import Config
from ..utils import now, minutes, parse_time_string, km_to_minutes
# Configure logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RapidAPIFetcher(TrainDataFetcher):
    """Fetch train data from RapidAPI."""
    
    def __init__(self):
        self.headers = {
            "X-RapidAPI-Key": Config.RAPIDAPI_KEY,
            "X-RapidAPI-Host": Config.RAPIDAPI_HOST
        }
    
    def fetch(self, station_code: str, hours: int) -> List[TrainETA]:
        """Fetch trains from RapidAPI."""
        try:
            url = f"https://{Config.RAPIDAPI_HOST}/api/v3/getLiveStation"
            params = {"stationCode": station_code, "hours": hours}
            
            response = requests.get(
                url, 
                headers=self.headers, 
                params=params, 
                timeout=Config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            return self._parse_rapidapi_response(response.json())
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch from RapidAPI: {e}")
            return []
    
    def _parse_rapidapi_response(self, data: Dict[str, Any]) -> List[TrainETA]:
        """Parse RapidAPI response."""
        trains = []
        base = now()
        
        # Try different possible data structures
        items = data.get("data") or data.get("trains") or []
        
        for item in items:
            try:
                train_no = str(item.get("trainNo") or item.get("train_number", "NA"))
                name = item.get("trainName") or item.get("name", "Unknown")
                
                # Parse ETA
                eta_min = item.get("etaMin")
                if eta_min is not None:
                    eta_station = base + minutes(int(eta_min))
                else:
                    time_str = item.get("expectedArrival") or item.get("arrivalTime")
                    eta_station = parse_time_string(time_str, base)
                    if not eta_station:
                        eta_station = base + minutes(30)
                
                # Calculate crossing ETA
                offset_min = km_to_minutes(
                    Config.DIST_KM_FROM_STATION,
                    Config.AVG_SPEED_KMPH
                )
                eta_crossing = eta_station - minutes(int(offset_min))
                
                # Parse delay
                delay = item.get("delayMin") or item.get("delay")
                
                trains.append(TrainETA(
                    train_no=train_no,
                    name=name,
                    eta_at_station=eta_station,
                    eta_at_crossing=eta_crossing,
                    source="rapidapi",
                    delay_min=int(delay) if delay else None,
                    speed_kmph=Config.AVG_SPEED_KMPH
                ))
                
            except (ValueError, KeyError) as e:
                logger.debug(f"Failed to parse train item: {e}")
                continue
        
        return trains