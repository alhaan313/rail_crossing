# Auto-Refresh Functionality

## Overview

Your railway application now includes automatic data refresh functionality that updates train information at regular intervals without requiring users to manually reload the page.

## Features Added

### 🔄 Auto-Refresh Controls
- **Manual Refresh Button**: Instantly fetch the latest train data
- **Auto-Refresh Toggle**: Enable/disable automatic updates
- **Refresh Interval Selector**: Choose update frequency (10s, 30s, 1m, 2m, 5m)
- **Last Updated Indicator**: Shows when data was last refreshed and cache status

### 🚀 Performance Optimizations
- **In-Memory Caching**: Reduces API calls to Erail by caching data for 2 minutes
- **Smart Updates**: Only the necessary parts of the page are updated, preserving user interactions
- **Cache Status**: Shows whether data is served from cache or freshly fetched

### 📱 User Experience
- **Persistent Settings**: Auto-refresh preferences are saved in browser localStorage
- **Real-time Updates**: Hero section, train cards, and table are updated automatically
- **Countdown Timers**: Hero countdown is reinitialized after each update
- **Responsive Design**: Controls adapt to mobile and desktop layouts

## Usage

### For Users
1. **Enable Auto-Refresh**: Click the "Enable Auto-refresh" button
2. **Choose Interval**: Select how often you want updates (default: 30 seconds)
3. **Manual Updates**: Use the "🔄 Refresh Now" button for immediate updates
4. **Settings Persistence**: Your preferences are automatically saved

### For Developers

#### API Endpoints
```
GET /api/trains
```
Returns JSON with:
```json
{
  "success": true,
  "trains": [...],
  "next_train": {...},
  "total_trains": 25,
  "timestamp": 1758057603295,
  "cache_info": {
    "cached": true,
    "age_seconds": 15.3,
    "ttl_minutes": 2
  }
}
```

#### JavaScript Functions
- `toggleAutoRefresh()`: Enable/disable auto-refresh
- `changeRefreshInterval(seconds)`: Change update frequency
- `manualRefresh()`: Force immediate update
- `updateTrainData(data)`: Update page content with new data

#### Cache Configuration
```python
TRAIN_DATA_CACHE = {
    'data': None,
    'timestamp': None,
    'ttl_minutes': 2  # Configurable cache duration
}
```

## Technical Implementation

### Frontend (JavaScript)
- **AJAX Updates**: Uses `fetch()` to get data from `/api/trains`
- **DOM Manipulation**: Updates hero section, cards, and table without page reload
- **Timer Management**: `setInterval()` for auto-refresh with proper cleanup
- **Local Storage**: Persists user preferences across sessions

### Backend (Flask)
- **Caching Layer**: Simple in-memory cache to reduce Erail API calls
- **Cache Management**: Automatic expiration and fresh data fetching
- **JSON API**: RESTful endpoint for frontend consumption
- **Error Handling**: Graceful degradation when API calls fail

### Cache Benefits
- **Reduced Load**: Minimizes requests to external Erail API
- **Faster Response**: Cached data serves instantly
- **Better UX**: Consistent response times
- **Cost Effective**: Reduces external API usage if rate-limited

## Configuration Options

### Refresh Intervals
- 10 seconds (for testing/development)
- 30 seconds (default, good balance)
- 1 minute (moderate usage)
- 2 minutes (light usage)  
- 5 minutes (minimal usage)

### Cache Settings
Change `TRAIN_DATA_CACHE['ttl_minutes']` in `app.py` to adjust cache duration.

## Browser Compatibility
- Modern browsers with `fetch()` support
- localStorage for settings persistence
- CSS Grid and Flexbox for responsive controls

## Testing

Run the test script:
```bash
python test_auto_refresh.py
```

This verifies:
- API endpoint functionality
- JSON response structure
- Caching behavior
- Error handling

## Production Considerations

1. **Cache Duration**: 2 minutes is optimal for live data vs. performance
2. **Memory Usage**: In-memory cache is lost on server restart
3. **Scaling**: Consider Redis for multi-instance deployments  
4. **Rate Limiting**: Built-in caching reduces external API calls
5. **Error Handling**: Graceful fallbacks when refresh fails

## Future Enhancements

- **Visual Indicators**: Loading spinners during updates
- **Smart Refresh**: Update only changed trains
- **Push Notifications**: WebSocket for real-time updates
- **Service Worker**: Offline caching and background sync
- **Progressive Enhancement**: Works without JavaScript

## Files Modified

- `app.py`: Added API endpoint and caching
- `static/main.js`: Auto-refresh functionality
- `static/styles.css`: Control styling
- `templates/index.html`: UI controls
- `test_auto_refresh.py`: Testing script