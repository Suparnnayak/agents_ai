"""
Quick local API test script

Usage:
    1. Start API: uvicorn app:app --port 8000
    2. Run this: python test_local.py
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_all():
    """Test all endpoints."""
    print("=" * 70)
    print("Testing Hospital Forecast API")
    print(f"Base URL: {BASE_URL}")
    print("=" * 70)
    
    # Test 1: Root
    print("\n[1/4] Testing Root Endpoint (GET /)")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        r.raise_for_status()
        print(f"   Status: {r.status_code}")
        print(f"   Response: {json.dumps(r.json(), indent=2)}")
    except Exception as e:
        print(f"   ERROR: {e}")
        return
    
    # Test 2: Health
    print("\n[2/4] Testing Health Check (GET /health)")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        r.raise_for_status()
        data = r.json()
        print(f"   Status: {r.status_code}")
        print(f"   Model loaded: {data.get('model_loaded')}")
        print(f"   Data loaded: {data.get('data_loaded')}")
        if not data.get('model_loaded'):
            print("   WARNING: Model not loaded!")
    except Exception as e:
        print(f"   ERROR: {e}")
        return
    
    # Test 3: Hospitals
    print("\n[3/4] Testing List Hospitals (GET /hospitals)")
    try:
        r = requests.get(f"{BASE_URL}/hospitals", timeout=5)
        r.raise_for_status()
        data = r.json()
        print(f"   Status: {r.status_code}")
        print(f"   Found {data.get('count')} hospitals")
        print(f"   Hospitals: {data.get('hospitals', [])[:5]}...")  # Show first 5
    except Exception as e:
        print(f"   ERROR: {e}")
        return
    
   # Test 4: Predict
print("\n[4/4] Testing Predict (POST /predict)")
try:
    payload = {
    "hospital_ids": ["INVALID"],
    "horizons": [1]
}


    r = requests.post(
        f"{BASE_URL}/predict",
        json=payload,
        timeout=30
    )
    r.raise_for_status()
    data = r.json()

    print(f"   Status: {r.status_code}")
    print(f"   Generated {data.get('count')} forecasts")

    # STRUCTURE CHECK
    forecasts = data.get("forecasts", [])
    assert len(forecasts) == 6, "Unexpected forecast count!"

    required_keys = {"hospital_id", "horizon", "prediction"}
    for f in forecasts:
        assert required_keys.issubset(f.keys()), f"Missing keys in forecast: {f}"

    print("   Structure validation passed ✅")
    print(f"   Sample: {forecasts[0]}")

except requests.exceptions.HTTPError as e:
    print(f"   HTTP ERROR: {e}")
    if e.response:
        print(f"   Details: {e.response.text}")
except AssertionError as e:
    print(f"   VALIDATION ERROR: {e}")
except Exception as e:
    print(f"   ERROR: {e}")

    print("\n" + "=" * 70)
    print("Testing Complete!")
    print("=" * 70)

if __name__ == "__main__":
    test_all()

