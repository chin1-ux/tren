import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')

def test_timeline_endpoint():
    """Test the timeline API endpoint"""
    # Test with a real trend ID
    trend_id = 1  # Replace with actual trend ID
    
    response = requests.get(f"{BASE_URL}/api/trends/{trend_id}/timeline")
    assert response.status_code == 200
    
    data = response.json()
    assert 'velocity_history' in data
    assert 'first_detected_at' in data
    assert 'peak_velocity' in data
    assert 'velocity_acceleration_pct' in data
    assert 'snapshot_count' in data
    
    print("OK: Timeline endpoint working")

def test_peaking_trends_endpoint():
    """Test the peaking trends endpoint"""
    response = requests.get(f"{BASE_URL}/api/trends/peaking?limit=5")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    
    for trend in data:
        assert 'peaking_score' in trend
        assert trend['peaking_score'] >= 70
    
    print("OK: Peaking trends endpoint working")

if __name__ == "__main__":
    test_timeline_endpoint()
    test_peaking_trends_endpoint()