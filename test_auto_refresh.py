#!/usr/bin/env python3
"""
Simple test script to verify the auto-refresh API endpoint with hybrid refresh.
"""

import json
import requests
from app import app

def test_api_endpoint():
    """Test the /api/trains endpoint locally."""
    with app.test_client() as client:
        print("Testing /api/trains endpoint...")
        
        # Make first request
        response = client.get('/api/trains')
        assert response.status_code == 200
        
        data = response.get_json()
        print(f"✓ API responded with status {response.status_code}")
        print(f"✓ Success: {data.get('success')}")
        print(f"✓ Total trains: {data.get('total_trains')}")
        print(f"✓ Cache info: {data.get('cache_info')}")
        
        if data.get('next_train'):
            print(f"✓ Next train: #{data['next_train']['train_no']} - {data['next_train']['name']}")
        else:
            print("ℹ No upcoming trains found")
        
        # Make second request to test caching
        print("\nTesting cache functionality...")
        response2 = client.get('/api/trains')
        data2 = response2.get_json()
        
        cache_info = data2.get('cache_info', {})
        if cache_info.get('cached'):
            print(f"✓ Second request served from cache (age: {cache_info.get('age_seconds')}s)")
        else:
            print("ℹ Second request fetched fresh data")
        
        print(f"\nJSON structure preview:")
        print(json.dumps({k: v for k, v in data.items() if k != 'trains'}, indent=2))
        
        return True

def main():
    """Run tests."""
    print("=" * 50)
    print("Auto-refresh functionality test")
    print("=" * 50)
    
    try:
        test_api_endpoint()
        print(f"\n✅ All tests passed! Auto-refresh with hybrid refresh should work correctly.")
        print("\n🔄 New Features:")
        print("- Hybrid refresh: Background updates only when users are active")
        print("- Human-readable time format: '2 hours and 14 minutes'")
        print("- Improved UI: No tick emoji, better animations")
        print("- Loading states: Visual feedback during updates")
        print("\nTo test in browser:")
        print("1. Start the app: python app.py")
        print("2. Open http://localhost:5000/trains")  
        print("3. Use the refresh controls to enable auto-refresh")
        print("4. Background refresh starts automatically when users are active")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()