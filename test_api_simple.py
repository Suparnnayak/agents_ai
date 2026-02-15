"""
Simple test script for Hospital Forecast API (no color output)

Usage:
    python test_api_simple.py
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://hospital-forecasting.onrender.com"


def test_root():
    """Test GET / endpoint."""
    print("\n" + "="*60)
    print("Testing: Root Endpoint (GET /)")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_health():
    """Test GET /health endpoint."""
    print("\n" + "="*60)
    print("Testing: Health Check (GET /health)")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_hospitals():
    """Test GET /hospitals endpoint."""
    print("\n" + "="*60)
    print("Testing: List Hospitals (GET /hospitals)")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/hospitals", timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"Found {data['count']} hospitals: {data['hospitals']}")
        return True, data.get("hospitals", [])
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, []


def test_predict_default():
    """Test POST /predict with default parameters."""
    print("\n" + "="*60)
    print("Testing: Predict (Default) (POST /predict)")
    print("="*60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/predict",
            json={},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"Generated {data['count']} forecasts")
        if data.get("forecasts"):
            print(f"Sample forecast: {json.dumps(data['forecasts'][0], indent=2, default=str)}")
        return True
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Error response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_predict_specific(hospital_ids):
    """Test POST /predict with specific hospitals."""
    print("\n" + "="*60)
    print("Testing: Predict (Specific Hospitals) (POST /predict)")
    print("="*60)
    
    if not hospital_ids:
        print("❌ No hospital IDs available")
        return False
    
    try:
        payload = {
            "hospital_ids": hospital_ids[:2],  # Use string IDs like 'HOSP_1'
            "horizons": [1, 2, 3, 7]
        }
        print(f"Request payload: {json.dumps(payload, indent=2)}")
        response = requests.post(
            f"{BASE_URL}/predict",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"Generated {data['count']} forecasts")
        if data.get("forecasts"):
            print(f"Sample forecast: {json.dumps(data['forecasts'][0], indent=2, default=str)}")
        return True
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Error response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("Hospital Forecast API Test Suite")
    print(f"Testing: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*60)
    
    results = []
    
    results.append(("Root", test_root()))
    results.append(("Health", test_health()))
    
    success, hospitals = test_hospitals()
    results.append(("Hospitals", success))
    
    results.append(("Predict (Default)", test_predict_default()))
    
    if hospitals:
        results.append(("Predict (Specific)", test_predict_specific(hospitals)))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{name:.<40} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ {total - passed} test(s) failed")


if __name__ == "__main__":
    main()

