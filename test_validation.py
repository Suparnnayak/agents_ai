"""
Test input validation for ForecastRequest.
"""

from app import ForecastRequest
from pydantic import ValidationError

def test_validation():
    """Test all validation rules."""
    print("=" * 70)
    print("INPUT VALIDATION TESTS")
    print("=" * 70)
    print()
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Empty hospital_ids
    print("[1/5] Testing empty hospital_ids...")
    try:
        r = ForecastRequest(hospital_ids=[], horizons=[1, 2])
        print("   [FAIL] Should reject empty hospital_ids")
        tests_failed += 1
    except ValidationError:
        print("   [PASS] Empty hospital_ids rejected")
        tests_passed += 1
    print()
    
    # Test 2: Horizon < 1
    print("[2/5] Testing horizon < 1...")
    try:
        r = ForecastRequest(hospital_ids=['HOSP_1'], horizons=[0, 1])
        print("   [FAIL] Should reject horizon < 1")
        tests_failed += 1
    except ValidationError:
        print("   [PASS] Horizon < 1 rejected")
        tests_passed += 1
    print()
    
    # Test 3: Horizon > 7
    print("[3/5] Testing horizon > 7...")
    try:
        r = ForecastRequest(hospital_ids=['HOSP_1'], horizons=[1, 8])
        print("   [FAIL] Should reject horizon > 7")
        tests_failed += 1
    except ValidationError:
        print("   [PASS] Horizon > 7 rejected")
        tests_passed += 1
    print()
    
    # Test 4: Duplicate hospital_ids
    print("[4/5] Testing duplicate hospital_ids...")
    try:
        r = ForecastRequest(hospital_ids=['HOSP_1', 'HOSP_1'], horizons=[1, 2])
        print("   [FAIL] Should reject duplicate hospital_ids")
        tests_failed += 1
    except ValidationError:
        print("   [PASS] Duplicate hospital_ids rejected")
        tests_passed += 1
    print()
    
    # Test 5: Valid request
    print("[5/5] Testing valid request...")
    try:
        r = ForecastRequest(hospital_ids=['HOSP_1', 'HOSP_2'], horizons=[1, 2, 3])
        print(f"   [PASS] Valid request accepted")
        print(f"   Hospitals: {r.hospital_ids}")
        print(f"   Horizons: {r.horizons} (sorted: {r.horizons == sorted(r.horizons)})")
        tests_passed += 1
    except ValidationError as e:
        print(f"   [FAIL] Valid request rejected: {e}")
        tests_failed += 1
    print()
    
    print("=" * 70)
    print(f"RESULTS: {tests_passed} passed, {tests_failed} failed")
    print("=" * 70)
    
    return tests_failed == 0

if __name__ == "__main__":
    success = test_validation()
    exit(0 if success else 1)

