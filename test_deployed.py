"""
Comprehensive test for deployed API at https://agents-ai-1-p4s6.onrender.com
"""

import requests
import json

BASE_URL = "https://agents-ai-1-p4s6.onrender.com"

def test_all():
    """Test all endpoints comprehensively."""
    print("=" * 70)
    print("COMPREHENSIVE API TEST")
    print(f"Testing: {BASE_URL}")
    print("=" * 70)
    print()
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Root
    print("[1/7] Testing Root Endpoint (GET /)")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=10)
        r.raise_for_status()
        data = r.json()
        assert data.get("status") == "Hospital Forecast API running"
        print(f"   [PASS] Status: {r.status_code}")
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        tests_failed += 1
    print()
    
    # Test 2: Health
    print("[2/7] Testing Health Check (GET /health)")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        r.raise_for_status()
        data = r.json()
        assert data.get("model_loaded") == True
        assert data.get("data_loaded") == True
        print(f"   [PASS] Model and data loaded")
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        tests_failed += 1
    print()
    
    # Test 3: Model Info
    print("[3/7] Testing Model Info (GET /model-info)")
    try:
        r = requests.get(f"{BASE_URL}/model-info", timeout=10)
        r.raise_for_status()
        data = r.json()
        assert "feature_count" in data
        assert "feature_columns" in data
        print(f"   [PASS] Model info retrieved")
        print(f"   Version: {data.get('version')}")
        print(f"   Features: {data.get('feature_count')}")
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        tests_failed += 1
    print()
    
    # Test 4: Hospitals
    print("[4/7] Testing List Hospitals (GET /hospitals)")
    try:
        r = requests.get(f"{BASE_URL}/hospitals", timeout=10)
        r.raise_for_status()
        data = r.json()
        hospitals = data.get("hospitals", [])
        assert len(hospitals) > 0
        print(f"   [PASS] Found {len(hospitals)} hospitals")
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        tests_failed += 1
    print()
    
    # Test 5: Predict (Valid)
    print("[5/7] Testing Predict (Valid Request)")
    try:
        payload = {
            "hospital_ids": ["HOSP_1", "HOSP_2"],
            "horizons": [1, 2, 3]
        }
        r = requests.post(f"{BASE_URL}/predict", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        assert data.get("count") == 6  # 2 hospitals * 3 horizons
        assert len(data.get("forecasts", [])) == 6
        print(f"   [PASS] Generated {data.get('count')} forecasts")
        if "metadata" in data:
            print(f"   Inference time: {data['metadata'].get('inference_time_seconds')}s")
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        tests_failed += 1
    print()
    
    # Test 6: Predict (Invalid - Unknown Hospital)
    print("[6/7] Testing Predict (Invalid Hospital - Should Return 400)")
    try:
        payload = {
            "hospital_ids": ["INVALID_HOSP"],
            "horizons": [1, 2]
        }
        r = requests.post(f"{BASE_URL}/predict", json=payload, timeout=10)
        if r.status_code == 400:
            print(f"   [PASS] Correctly rejected invalid hospital (HTTP 400)")
            tests_passed += 1
        else:
            print(f"   [FAIL] Expected HTTP 400, got {r.status_code}")
            tests_failed += 1
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            print(f"   [PASS] Correctly rejected invalid hospital (HTTP 400)")
            tests_passed += 1
        else:
            print(f"   [FAIL] Expected HTTP 400, got {e.response.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        tests_failed += 1
    print()
    
    # Test 7: Predict (Invalid - Horizon > 7)
    print("[7/7] Testing Predict (Invalid Horizon - Should Return 400/422)")
    try:
        payload = {
            "hospital_ids": ["HOSP_1"],
            "horizons": [8]  # Invalid
        }
        r = requests.post(f"{BASE_URL}/predict", json=payload, timeout=10)
        # Pydantic returns 422 for validation errors, which is correct
        if r.status_code in [400, 422]:
            print(f"   [PASS] Correctly rejected invalid horizon (HTTP {r.status_code})")
            tests_passed += 1
        else:
            print(f"   [FAIL] Expected HTTP 400/422, got {r.status_code}")
            tests_failed += 1
    except requests.exceptions.HTTPError as e:
        # Pydantic returns 422 for validation errors
        if e.response.status_code in [400, 422]:
            print(f"   [PASS] Correctly rejected invalid horizon (HTTP {e.response.status_code})")
            tests_passed += 1
        else:
            print(f"   [FAIL] Expected HTTP 400/422, got {e.response.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        tests_failed += 1
    print()
    
    # Summary
    print("=" * 70)
    print(f"TEST SUMMARY: {tests_passed} passed, {tests_failed} failed")
    print("=" * 70)
    
    return tests_failed == 0

if __name__ == "__main__":
    success = test_all()
    exit(0 if success else 1)

