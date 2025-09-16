import re
import logging
import requests
from typing import List, Optional
from datetime import timedelta, datetime
import pytz

from railway_app_v2.config import Config
from railway_app_v2.models import TrainETA
from railway_app_v2.fetchers.base import TrainDataFetcher
from railway_app_v2.utils import km_to_minutes, parse_time_string, minutes

logger = logging.getLogger(__name__)


class ErailFetcher(TrainDataFetcher):
    """Fetch train data from Erail.in."""
    
    ERAIL_URL = "https://erail.in/rail/getTrains.aspx"
    
    # Headers to make request look more like a browser
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1"
    }
    
    @staticmethod
    def _safe_get(lst, idx, default=""):
        return lst[idx] if idx < len(lst) else default

    @staticmethod
    def _normalize_hhmm(s: str) -> Optional[str]:
        if not s:
            return None
        s = s.strip().replace('.', ':').replace(' ', '')
        m = re.fullmatch(r'(\d{1,2}):(\d{2})', s)
        if not m:
            return None
        try:
            ih, im = int(m.group(1)), int(m.group(2))
            if 0 <= ih <= 23 and 0 <= im <= 59:
                return f"{ih:02d}:{im:02d}"
        except ValueError:
            return None
        return None

    @classmethod
    def _first_time_candidate(cls, fields_slice) -> Optional[str]:
        for tok in fields_slice:
            t = cls._normalize_hhmm(tok)
            if t:
                return t
        return None
    
    def fetch(self, station_code: str, hours: int) -> List[TrainETA]:
        """Fetch trains from erail.in."""
        try:
            params = {
                "Station_From": station_code,
                "Station_To": station_code,
                "DataSource": 0,
                "Language": 0,
                "Cache": "true"
            }
            
            logger.info(f"Making request to Erail API with params: {params}")
            response = requests.get(
                self.ERAIL_URL, 
                params=params, 
                headers=self.HEADERS,
                timeout=Config.REQUEST_TIMEOUT
            )
            logger.info(f"Erail API response status: {response.status_code}")
            response.raise_for_status()
            
            if not response.text:
                logger.error("Erail API returned empty response")
                return []
                
            trains = self._parse_erail_response(response.text, station_code, hours)
            logger.info(f"Successfully parsed {len(trains)} trains from Erail response")
            return trains
            
        except requests.Timeout:
            logger.error(f"Timeout ({Config.REQUEST_TIMEOUT}s) while fetching from Erail")
            return []
        except requests.ConnectionError as e:
            logger.error(f"Connection error while fetching from Erail: {e}")
            return []
        except requests.RequestException as e:
            logger.error(f"Failed to fetch from Erail: {type(e).__name__}: {e}")
            return []
    
    def _parse_erail_response(self, raw_text: str, station_code: str, hours: int) -> List[TrainETA]:
        """
        Parse Erail getTrains.aspx 'raw_text' into List[TrainETA].

        Notes on field layout (as observed from Erail response):
        0  train_no
        1  train_name
        2  src_name
        3  src_code
        4  dst_name
        5  dst_code
        6  via_name
        7  via_code
        8  final_dst_name
        9  final_dst_code
        10 arr_time at queried station (e.g., VN)
        11 dep_time (often destination arrival/dep field)
        12 travel_time (e.g., '07.25')
        13 days string ('1111111' daily, etc.)
        29 type (if present)

        The Erail payload may contain short/metadata blocks like:
        "~VN~Vaniyambadi~~~~2025-8-26-0-8-6~~~..."
        These are skipped via validation checks.
        """ 

        trains: List[TrainETA] = []
        # Use Indian timezone for base time
        ist = pytz.timezone('Asia/Kolkata')
        base = datetime.now(ist)

        if not raw_text:
            logger.warning("Empty Erail response")
            return trains

        # Split into records, strip empties
        records = [blk.strip() for blk in raw_text.split("^") if blk.strip()]
        
    
        for rec in records:
            parts = rec.split("~")

            # Basic sanity: many meta lines are too short or don't start with a train no
            if len(parts) < 14:
                continue

            train_no = self._safe_get(parts, 0, "").strip()
            train_name = self._safe_get(parts, 1, "").strip()

            # Train number should be mostly digits (allow a leading alpha in rare cases, but reject empty/garbage)
            if not train_no or not any(ch.isdigit() for ch in train_no):
                continue

            # Core fields (not strictly needed for TrainETA but useful if you log/extend later)
            src_name, src_code = self._safe_get(parts, 2, "").strip(), self._safe_get(parts, 3, "").strip()
            dst_name, dst_code = self._safe_get(parts, 4, "").strip(), self._safe_get(parts, 5, "").strip()
            via_name, via_code = self._safe_get(parts, 6, "").strip(), self._safe_get(parts, 7, "").strip()
            final_dst_name, final_dst_code = self._safe_get(parts, 8, "").strip(), self._safe_get(parts, 9, "").strip()

            # Arrival at the queried station is typically at index 10.
            arr_raw = self._safe_get(parts, 10, "").strip()

            # Robust time normalization (handles '06.20' etc.)
            arr_hhmm = self._normalize_hhmm(arr_raw)

            # Fallback: scan nearby fields if 10 is blank/malformed
            if not arr_hhmm:
                arr_hhmm = self._first_time_candidate(parts[10:16])

            if not arr_hhmm:
                # No parseable arrival time → skip
                logger.debug(f"Skipping train {train_no} - no parseable arrival time (raw='{arr_raw}').")
                continue

            # Convert to datetime (handles tomorrow rollover)

            eta_station = parse_time_string(arr_hhmm, base)
            if not eta_station:
                logger.debug(f"Skipping train {train_no} - parse_time_string failed (norm='{arr_hhmm}').")
                continue
            
            # Compute ETA at crossing by subtracting travel time from station to crossing
            offset_min = km_to_minutes(Config.DIST_KM_FROM_STATION, Config.AVG_SPEED_KMPH)
            # Round to nearest minute to avoid off-by-1 jitter
            eta_crossing = eta_station - minutes(int(round(offset_min)))

            # Filter out trains that have already passed or are too far in the future
            # Use Indian timezone for current time
            now = datetime.now(pytz.timezone('Asia/Kolkata'))
            if eta_crossing < now:
                logger.debug(f"Skipping train {train_no} - already passed (eta was {eta_crossing})")
                continue
            
            if eta_crossing > now + timedelta(hours=hours):
                logger.debug(f"Skipping train {train_no} - too far in future (eta {eta_crossing})")
                continue

            trains.append(TrainETA(
                train_no=train_no,
                name=train_name,
                eta_at_station=eta_station,
                eta_at_crossing=eta_crossing,
                source="erail",
                delay_min=None,
                speed_kmph=Config.AVG_SPEED_KMPH
            ))

        # Optional: de-duplicate by (train_no, eta_at_crossing minute)
        keyd = {}

        for t in trains:
            key = (t.train_no, t.eta_at_crossing.replace(second=0, microsecond=0))
            # Keep earliest crossing if duplicates
            if key not in keyd or t.eta_at_crossing < keyd[key].eta_at_crossing:
                keyd[key] = t

        result = sorted(keyd.values(), key=lambda x: x.eta_at_crossing)

        return result


if __name__ == "__main__":

    from dataclasses import asdict
    from pprint import pprint
    
    erail = ErailFetcher()
    trains = erail.fetch('VN', 2)

    for t in trains:
        print('\n')
        pprint(asdict(t))
