import logging, math, time, threading
from datetime import datetime, timedelta
import pytz
from flask import Flask, render_template, request, url_for, redirect, jsonify

from railway_app_v2.fetchers.erail import ErailFetcher
from railway_app_v2.fetchers.overpass import OverpassFetcher

app = Flask(__name__, static_folder='static', template_folder='templates')
logging.basicConfig(level=logging.INFO)

# Simple in-memory cache with hybrid refresh
TRAIN_DATA_CACHE = {
    'data': None,
    'timestamp': None,
    'ttl_minutes': 2,  # Cache for 2 minutes
    'last_user_activity': None,
    'background_refresh_active': False
}

# Background refresh settings
BACKGROUND_REFRESH_INTERVAL = 90  # seconds
USER_ACTIVITY_TIMEOUT = 300  # 5 minutes

PAGE_SIZE = 10


def is_cache_valid():
    """Check if cached data is still valid."""
    if not TRAIN_DATA_CACHE['timestamp'] or not TRAIN_DATA_CACHE['data']:
        return False
    
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    cache_age = now - TRAIN_DATA_CACHE['timestamp']
    if cache_age.total_seconds() >= (TRAIN_DATA_CACHE['ttl_minutes'] * 60):
        return False
    
    # Invalidate cache if next train has passed
    next_train = TRAIN_DATA_CACHE['data'][0] if TRAIN_DATA_CACHE['data'] else None
    if next_train and next_train.eta_at_crossing < now:
        logging.info(f"Invalidating cache because next train {next_train.train_no} has passed (ETA: {next_train.eta_at_crossing}, Now: {now})")
        return False
    
    return True


def record_user_activity():
    """Record that a user is actively using the app."""
    TRAIN_DATA_CACHE['last_user_activity'] = datetime.now()
    if not TRAIN_DATA_CACHE['background_refresh_active']:
        start_background_refresh()


def is_user_active():
    """Check if users have been active recently."""
    if not TRAIN_DATA_CACHE['last_user_activity']:
        return False
    
    inactive_time = datetime.now() - TRAIN_DATA_CACHE['last_user_activity']
    return inactive_time.total_seconds() < USER_ACTIVITY_TIMEOUT


def fetch_fresh_train_data():
    """Fetch fresh train data from Erail."""
    logging.info("Fetching fresh train data from Erail")
    erail = ErailFetcher()
    all_trains = erail.fetch("VN", 100) or []
    all_trains = sorted(all_trains, key=lambda t: getattr(t, "eta_at_crossing", None) or 9e18)
    
    # Update cache
    TRAIN_DATA_CACHE['data'] = all_trains
    TRAIN_DATA_CACHE['timestamp'] = datetime.now(pytz.timezone('Asia/Kolkata'))
    
    return all_trains


def background_refresh_worker():
    """Background worker that refreshes data when users are active."""
    while TRAIN_DATA_CACHE['background_refresh_active']:
        try:
            if is_user_active():
                # Refresh data proactively if cache is getting stale
                cache_age = 0
                if TRAIN_DATA_CACHE['timestamp']:
                    cache_age = (datetime.now() - TRAIN_DATA_CACHE['timestamp']).total_seconds()
                
                if cache_age > 60:  # Refresh if data is older than 1 minute
                    logging.info("Background refresh: updating train data")
                    fetch_fresh_train_data()
            else:
                # Stop background refresh if no users are active
                logging.info("No active users, stopping background refresh")
                TRAIN_DATA_CACHE['background_refresh_active'] = False
                break
                
        except Exception as e:
            logging.error(f"Background refresh error: {e}")
        
        time.sleep(BACKGROUND_REFRESH_INTERVAL)


def start_background_refresh():
    """Start background refresh if not already running."""
    if not TRAIN_DATA_CACHE['background_refresh_active']:
        TRAIN_DATA_CACHE['background_refresh_active'] = True
        thread = threading.Thread(target=background_refresh_worker, daemon=True)
        thread.start()
        logging.info("Started background refresh worker")


def get_cached_trains():
    """Get trains from cache if valid, otherwise fetch fresh data."""
    record_user_activity()  # Track user activity
    
    if is_cache_valid() and TRAIN_DATA_CACHE['data']:
        logging.info("Returning cached train data")
        return TRAIN_DATA_CACHE['data']
    
    # Fetch fresh data
    return fetch_fresh_train_data()


@app.route("/")
def home():
    return redirect(url_for("trains"))

@app.route("/trains")
def trains():
    all_trains = get_cached_trains()
    next_train = all_trains[0] if all_trains else None

    page = max(1, int(request.args.get("page", 1)))
    total_pages = max(1, math.ceil(len(all_trains) / PAGE_SIZE))
    page = min(page, total_pages)
    start, end = (page - 1) * PAGE_SIZE, (page - 1) * PAGE_SIZE + PAGE_SIZE
    page_trains = all_trains[start:end]

    def build_pages(current, total_pages, window=1):
        pages = []
        for p in range(1, total_pages + 1):
            if p == 1 or p == total_pages or abs(p - current) <= window:
                pages.append(p)
            elif pages and pages[-1] != "...":
                pages.append("...")
        return pages

    pages = build_pages(page, total_pages)
    return render_template("index.html",
                           trains=page_trains, next_train=next_train,
                           page=page, total_pages=total_pages, pages=pages)

@app.route("/crossings")
def crossings():
    data = OverpassFetcher.fetch_crossings()
    show_all = request.args.get("all") == "1"
    show_list = data["crossings"] if show_all else data["crossings"][:5]
    
    return render_template("crossings.html",
                           station=data["station"],
                           crossings=show_list,
                           total=data["total"],
                           showing=len(show_list),
                           show_all=show_all)

@app.route("/help")
def help_page():
    return render_template("help.html")

@app.route("/api/trains")
def api_trains():
    """API endpoint to get train data as JSON for AJAX updates."""
    try:
        all_trains = get_cached_trains()
        next_train = all_trains[0] if all_trains else None
        
        # Convert trains to JSON-serializable format
        trains_data = []
        for train in all_trains:
            trains_data.append({
                'train_no': train.train_no,
                'name': train.name,
                'eta_at_crossing': train.eta_at_crossing.isoformat(),
                'eta_at_crossing_formatted': train.eta_at_crossing.strftime("%I:%M %p"),
                'source': train.source
            })
        
        next_train_data = None
        if next_train:
            next_train_data = {
                'train_no': next_train.train_no,
                'name': next_train.name,
                'eta_at_crossing': next_train.eta_at_crossing.isoformat(),
                'eta_at_crossing_formatted': next_train.eta_at_crossing.strftime("%I:%M %p"),
                'source': next_train.source
            }
        
        # Add cache information
        cache_age_seconds = 0
        if TRAIN_DATA_CACHE['timestamp']:
            cache_age_seconds = (datetime.now() - TRAIN_DATA_CACHE['timestamp']).total_seconds()
        
        return jsonify({
            'success': True,
            'trains': trains_data,
            'next_train': next_train_data,
            'total_trains': len(all_trains),
            'timestamp': math.floor(time.time() * 1000),
            'timezone': 'Asia/Kolkata',
            'cache_info': {
                'cached': is_cache_valid(),
                'age_seconds': round(cache_age_seconds, 1),
                'ttl_minutes': TRAIN_DATA_CACHE['ttl_minutes']
            }
        })
    
    except Exception as e:
        logging.error(f"Error fetching train data: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'trains': [],
            'next_train': None,
            'total_trains': 0
        }), 500

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
