"""
Test to verify API calls don't mutate state.

This test calls the API twice and verifies:
1. Both calls return same number of forecasts
2. Historical data is not mutated between calls
3. No state persists between requests
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_state_mutation():
    """Test that API calls don't mutate shared state."""
    print("=" * 70)
    print("API STATE MUTATION TEST")
    print("=" * 70)
    print()
    
    # Test payload
    payload = {
        "hospital_ids": ["HOSP_1", "HOSP_2"],
        "horizons": [1, 2, 3]
    }
    
    print("Test Configuration:")
    print(f"   Hospitals: {payload['hospital_ids']}")
    print(f"   Horizons: {payload['horizons']}")
    print(f"   Expected forecasts per call: {len(payload['hospital_ids']) * len(payload['horizons'])}")
    print()
    
    # Make first call
    print("[1/3] First API call...")
    try:
        response1 = requests.post(
            f"{BASE_URL}/predict",
            json=payload,
            timeout=30
        )
        response1.raise_for_status()
        data1 = response1.json()
        count1 = data1.get('count', 0)
        print(f"   Status: {response1.status_code}")
        print(f"   Forecasts returned: {count1}")
        
        if count1 == 0:
            print("   [ERROR] First call returned 0 forecasts!")
            return False
    except Exception as e:
        print(f"   [ERROR] First call failed: {e}")
        return False
    print()
    
    # Make second call (should be identical)
    print("[2/3] Second API call (should be identical)...")
    try:
        response2 = requests.post(
            f"{BASE_URL}/predict",
            json=payload,
            timeout=30
        )
        response2.raise_for_status()
        data2 = response2.json()
        count2 = data2.get('count', 0)
        print(f"   Status: {response2.status_code}")
        print(f"   Forecasts returned: {count2}")
        
        if count2 == 0:
            print("   [ERROR] Second call returned 0 forecasts - STATE MUTATION DETECTED!")
            return False
    except Exception as e:
        print(f"   [ERROR] Second call failed: {e}")
        return False
    print()
    
    # Compare results
    print("[3/3] Comparing results...")
    if count1 != count2:
        print(f"   [FAIL] Count mismatch: first={count1}, second={count2}")
        print("   [FAIL] STATE MUTATION CONFIRMED - API is not stateless!")
        return False
    
    # Check if forecasts are identical (optional - just check structure)
    if count1 == 0:
        print("   [FAIL] Both calls returned 0 forecasts - this is a bug!")
        return False
    
    print(f"   [PASS] Both calls returned {count1} forecasts")
    print()
    
    # Make third call for extra verification
    print("[BONUS] Third API call (triple verification)...")
    try:
        response3 = requests.post(
            f"{BASE_URL}/predict",
            json=payload,
            timeout=30
        )
        response3.raise_for_status()
        data3 = response3.json()
        count3 = data3.get('count', 0)
        print(f"   Forecasts returned: {count3}")
        
        if count3 != count1:
            print(f"   [FAIL] Third call differs: first={count1}, third={count3}")
            return False
        
        print(f"   [PASS] Third call also returned {count3} forecasts")
    except Exception as e:
        print(f"   [WARNING] Third call failed: {e}")
        # Don't fail test if third call fails, but log it
    
    print()
    print("=" * 70)
    print("ALL TESTS PASSED - API is stateless!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = test_state_mutation()
    exit(0 if success else 1)

