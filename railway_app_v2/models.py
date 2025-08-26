from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum

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

@dataclass
class GateWindow:
    """Time window when gate should be closed."""
    start: datetime
    end: datetime
    trains: List[str] = field(default_factory=list)
    
    def is_active(self) -> bool:
        """Check if this window is currently active."""
        now = datetime.now()
        return self.start <= now <= self.end
    
    def duration_minutes(self) -> int:
        """Calculate window duration in minutes."""
        return int((self.end - self.start).total_seconds() // 60)

class DataSource(Enum):
    """Available data sources for train information."""
    SIMULATE = "simulate"
    RAPIDAPI = "rapidapi"
    ERAIL = "erail"
