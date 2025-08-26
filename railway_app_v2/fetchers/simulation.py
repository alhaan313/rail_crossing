from typing import List

from .base import TrainDataFetcher
from ..config import Config
from ..models import TrainETA
from ..utils import km_to_minutes, now, minutes

class SimulationFetcher(TrainDataFetcher):
    """Simulated train data for testing."""
    
    def fetch(self, station_code: str, hours: int) -> List[TrainETA]:
        """Return simulated trains."""
        base = now()
        samples = [
            ("12658", "Bengaluru Mail", 8, 0),
            ("22691", "Rajdhani Express", 15, 5),
            ("12864", "Howrah Express", 25, -2),
            ("16525", "Island Express", 35, 0),
        ]
        
        trains = []
        for train_no, name, minutes_to_station, delay in samples:
            if minutes_to_station <= hours * 60:
                eta_station = base + minutes(minutes_to_station)
                offset_min = km_to_minutes(Config.DIST_KM_FROM_STATION, Config.AVG_SPEED_KMPH)
                eta_crossing = eta_station - minutes(int(offset_min))
                
                trains.append(TrainETA(
                    train_no=train_no,
                    name=name,
                    eta_at_station=eta_station,
                    eta_at_crossing=eta_crossing,
                    source="simulated",
                    delay_min=delay if delay != 0 else None,
                    speed_kmph=Config.AVG_SPEED_KMPH
                ))
        
        return trains
