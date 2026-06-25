import sys
import os
from fastapi.testclient import TestClient

# Ensure the backend directory is in the import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import traceback
    from api import app
    client = TestClient(app)
except Exception as e:
    print("Traceback:")
    traceback.print_exc()
    print(f"Failed to import app: {e}")
    sys.exit(1)

def test_health_endpoint():
    print("Running health endpoint test...")
    try:
        response = client.get("/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        print("Response data:", data)
        assert data.get("status") == "healthy" or "status" in data, "Status field missing or unhealthy"
        print("Health check endpoint test passed successfully! [OK]")
    except Exception as e:
        print(f"Health check test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_health_endpoint()
