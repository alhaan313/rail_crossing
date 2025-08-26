import time, requests, os
import logging
from ..utils import haversine_km, dedupe_by_proximity

CITY_BBOX = os.environ.get("CITY_BBOX", "12.60,78.52,12.76,78.70")
OVERPASS_URL = os.environ.get("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
_CROSSINGS_CACHE = {"ts": 0, "data": None}

class OverpassFetcher:
    def __init__(self, city_bbox=CITY_BBOX, overpass_url=OVERPASS_URL):
        self.city_bbox = city_bbox
        self.overpass_url = overpass_url

    def fetch_crossings():
        now = time.time()
        if _CROSSINGS_CACHE["data"] and now - _CROSSINGS_CACHE["ts"] < 3600:
            return _CROSSINGS_CACHE["data"]

        # 1) Crossings + station
        q1 = f"""
    [out:json][timeout:25];
    (
    node["railway"="level_crossing"]({CITY_BBOX});
    node["railway"="crossing"]({CITY_BBOX});
    node["railway"="station"]["name"~"Vaniyambadi",i]({CITY_BBOX});
    );
    out body;
    """
        try:
            r = requests.post(OVERPASS_URL, data=q1, timeout=25)
            r.raise_for_status()
            nodes = r.json().get("elements", [])
        except Exception as e:
            logging.warning(f"Overpass q1 failed: {e}")
            return {"station": None, "crossings": [], "total": 0}

        station = next((n for n in nodes if n.get("tags", {}).get("railway") == "station"), None)
        st_lon = station.get("lon", 78.62) if station else 78.62
        st_lat = station.get("lat", 12.68) if station else 12.68

        raw_crossings = [
            {
                "id": n["id"],
                "name_tag": n.get("tags", {}).get("name") or n.get("tags", {}).get("name:en") or None,
                "lat": n["lat"],
                "lon": n["lon"]
            }
            for n in nodes
            if n.get("tags", {}).get("railway") in ("level_crossing", "crossing")
        ]
        # Deduplicate by proximity (and implicitly by id since id differs)
        raw_crossings = dedupe_by_proximity(raw_crossings, threshold_m=35)

        # 2) Named roads and places to craft friendly labels
        q2 = f"""
    [out:json][timeout:25];
    (
    way["highway"]["name"]({CITY_BBOX});
    node["place"]["name"]({CITY_BBOX});
    );
    out center;
    """
        roads, places = [], []
        try:
            r2 = requests.post(OVERPASS_URL, data=q2, timeout=25)
            r2.raise_for_status()
            for el in r2.json().get("elements", []):
                name = (el.get("tags") or {}).get("name")
                if not name: continue
                if el.get("type") == "way" and el.get("center"):
                    roads.append({"name": name, "lat": el["center"]["lat"], "lon": el["center"]["lon"]})
                elif el.get("type") == "node" and (el.get("tags") or {}).get("place"):
                    places.append({"name": name, "lat": el["lat"], "lon": el["lon"]})
        except Exception as e:
            logging.warning(f"Overpass q2 failed: {e}")

        enriched = []
        for c in raw_crossings:
            dist_km = haversine_km(st_lon, st_lat, c["lon"], c["lat"])
            # nearest named road
            nearest_road, min_r = None, 1e9
            for r in roads:
                d = haversine_km(c["lon"], c["lat"], r["lon"], r["lat"]); 
                if d < min_r: min_r, nearest_road = d, r
            # nearest place
            nearest_place, min_p = None, 1e9
            for p in places:
                d = haversine_km(c["lon"], c["lat"], p["lon"], p["lat"]); 
                if d < min_p: min_p, nearest_place = d, p

            label = c["name_tag"]
            if not label and nearest_road and min_r <= 1.0:
                label = f"{nearest_road['name']} Crossing"
            if not label and nearest_place and min_p <= 2.0:
                label = f"Near {nearest_place['name']} Crossing"
            if not label:
                label = "Level Crossing"

            enriched.append({
                "id": c["id"],
                "label": label,
                "road": nearest_road["name"] if nearest_road else None,
                "place": nearest_place["name"] if nearest_place else None,
                "lat": c["lat"], "lon": c["lon"],
                "distance_km": dist_km
            })

        # Final dedupe pass by label+location to avoid label duplicates after enrichment
        seen = set()
        final = []
        for e in enriched:
            key = (round(e["lat"], 5), round(e["lon"], 5), e["label"])
            if key in seen: continue
            seen.add(key)
            final.append(e)

        final.sort(key=lambda x: x["distance_km"])
        data = {
            "station": {"name": (station or {}).get("tags", {}).get("name", "Vaniyambadi"),
                        "lat": st_lat, "lon": st_lon},
            "crossings": final,
            "total": len(final)
        }
        _CROSSINGS_CACHE["ts"] = now
        _CROSSINGS_CACHE["data"] = data
        return data
