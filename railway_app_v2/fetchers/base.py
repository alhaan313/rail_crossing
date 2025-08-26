from typing import List
from railway_app_v2.models import TrainETA

class TrainDataFetcher:
    """Base class for train data fetchers."""
    
    def fetch(self, station_code: str, hours: int) -> List[TrainETA]:
        """Fetch train data. Must be implemented by subclasses."""
        raise NotImplementedError
