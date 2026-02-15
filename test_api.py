"""
Test script for Hospital Forecast API deployed at https://hospital-forecasting.onrender.com

Usage:
    python test_api.py
"""

import requests
import json
from typing import Dict, Any
from datetime import datetime

# API base URL
BASE_URL = "https://hospital-forecasting.onrender.com"

# Colors for terminal output (optional, works on most terminals)
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_test(name: str):
    """Print test header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}Testing: {name}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}❌ {message}{Colors.RESET}")


def print_info(message: str):
    """Print info message."""
    print(f"{Colors.YELLOW}ℹ️  {message}{Colors.RESET}")


def test_root_endpoint() -> bool:
    """Test GET / endpoint."""
    print_test("Root Endpoint (GET /)")
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print_success(f"Status Code: {response.status_code}")
        print_info(f"Response: {json.dumps(data, indent=2)}")
        
        # Validate response structure
        assert "status" in data, "Missing 'status' field"
        assert "version" in data, "Missing 'version' field"
        assert "endpoints" in data, "Missing 'endpoints' field"
        
        print_success("Root endpoint test passed!")
        return True
        
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return False
    except AssertionError as e:
        print_error(f"Validation failed: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def test_health_endpoint() -> bool:
    """Test GET /health endpoint."""
    print_test("Health Check Endpoint (GET /health)")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print_success(f"Status Code: {response.status_code}")
        print_info(f"Response: {json.dumps(data, indent=2)}")
        
        # Validate response structure
        assert "status" in data, "Missing 'status' field"
        assert "model_loaded" in data, "Missing 'model_loaded' field"
        assert "data_loaded" in data, "Missing 'data_loaded' field"
        
        # Check if model and data are loaded
        if data["model_loaded"]:
            print_success("Model is loaded")
        else:
            print_error("Model is NOT loaded")
            
        if data["data_loaded"]:
            print_success("Historical data is loaded")
        else:
            print_error("Historical data is NOT loaded")
        
        if data["status"] == "healthy":
            print_success("API is healthy!")
        else:
            print_error(f"API status: {data['status']}")
        
        print_success("Health check test passed!")
        return True
        
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return False
    except AssertionError as e:
        print_error(f"Validation failed: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def test_hospitals_endpoint() -> bool:
    """Test GET /hospitals endpoint."""
    print_test("List Hospitals Endpoint (GET /hospitals)")
    
    try:
        response = requests.get(f"{BASE_URL}/hospitals", timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print_success(f"Status Code: {response.status_code}")
        print_info(f"Response: {json.dumps(data, indent=2)}")
        
        # Validate response structure
        assert "hospitals" in data, "Missing 'hospitals' field"
        assert "count" in data, "Missing 'count' field"
        assert isinstance(data["hospitals"], list), "'hospitals' must be a list"
        assert data["count"] == len(data["hospitals"]), "Count mismatch"
        
        print_success(f"Found {data['count']} hospitals")
        print_info(f"Hospital IDs: {data['hospitals']}")
        
        print_success("Hospitals endpoint test passed!")
        return True, data["hospitals"] if "hospitals" in data else []
        
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return False, []
    except AssertionError as e:
        print_error(f"Validation failed: {e}")
        return False, []
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False, []


def test_predict_endpoint_default() -> bool:
    """Test POST /predict endpoint with default parameters (all hospitals, 7-day forecast)."""
    print_test("Predict Endpoint - Default (POST /predict)")
    
    try:
        payload = {}
        response = requests.post(
            f"{BASE_URL}/predict",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30  # Predictions may take longer
        )
        response.raise_for_status()
        
        data = response.json()
        print_success(f"Status Code: {response.status_code}")
        print_info(f"Response keys: {list(data.keys())}")
        
        # Validate response structure
        assert "status" in data, "Missing 'status' field"
        assert "forecasts" in data, "Missing 'forecasts' field"
        assert "count" in data, "Missing 'count' field"
        assert data["status"] == "success", f"Status is not 'success': {data['status']}"
        
        print_success(f"Generated {data['count']} forecasts")
        
        # Show sample forecast
        if data["forecasts"]:
            sample = data["forecasts"][0]
            print_info(f"Sample forecast: {json.dumps(sample, indent=2, default=str)}")
            
            # Validate forecast structure
            assert "hospital_id" in sample, "Missing 'hospital_id' in forecast"
            assert "horizon" in sample, "Missing 'horizon' in forecast"
            assert "forecast" in sample, "Missing 'forecast' in forecast"
        
        print_success("Predict endpoint (default) test passed!")
        return True
        
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print_error(f"Response: {e.response.text}")
        return False
    except AssertionError as e:
        print_error(f"Validation failed: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def test_predict_endpoint_specific_hospitals(hospital_ids: list) -> bool:
    """Test POST /predict endpoint with specific hospital IDs."""
    print_test("Predict Endpoint - Specific Hospitals (POST /predict)")
    
    if not hospital_ids:
        print_error("No hospital IDs available for testing")
        return False
    
    try:
        # Test with first 2 hospitals
        test_hospitals = hospital_ids[:2]
        payload = {
            "hospital_ids": test_hospitals,
            "horizons": [1, 2, 3, 7]  # Test specific horizons
        }
        
        print_info(f"Request payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{BASE_URL}/predict",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        print_success(f"Status Code: {response.status_code}")
        print_info(f"Generated {data['count']} forecasts")
        
        # Validate that only requested hospitals are returned
        returned_hospitals = set(f["hospital_id"] for f in data["forecasts"])
        expected_hospitals = set(test_hospitals)
        
        assert returned_hospitals.issubset(expected_hospitals), \
            f"Unexpected hospitals in response: {returned_hospitals - expected_hospitals}"
        
        # Validate horizons
        returned_horizons = set(f["horizon"] for f in data["forecasts"])
        expected_horizons = set(payload["horizons"])
        assert returned_horizons == expected_horizons, \
            f"Horizon mismatch. Expected: {expected_horizons}, Got: {returned_horizons}"
        
        print_success(f"Forecasts generated for hospitals: {sorted(returned_hospitals)}")
        print_success(f"Forecasts generated for horizons: {sorted(returned_horizons)}")
        
        print_success("Predict endpoint (specific hospitals) test passed!")
        return True
        
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print_error(f"Response: {e.response.text}")
        return False
    except AssertionError as e:
        print_error(f"Validation failed: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def test_predict_endpoint_single_horizon(hospital_ids: list) -> bool:
    """Test POST /predict endpoint with single horizon."""
    print_test("Predict Endpoint - Single Horizon (POST /predict)")
    
    if not hospital_ids:
        print_error("No hospital IDs available for testing")
        return False
    
    try:
        payload = {
            "hospital_ids": [hospital_ids[0]],  # Single hospital
            "horizons": [1],  # Single horizon
            "use_quantiles": False  # Test without quantiles
        }
        
        print_info(f"Request payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{BASE_URL}/predict",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        print_success(f"Status Code: {response.status_code}")
        print_info(f"Generated {data['count']} forecasts")
        
        # Should have exactly 1 forecast
        assert data["count"] == 1, f"Expected 1 forecast, got {data['count']}"
        
        forecast = data["forecasts"][0]
        assert forecast["hospital_id"] == hospital_ids[0], "Wrong hospital ID"
        assert forecast["horizon"] == 1, "Wrong horizon"
        
        print_success("Predict endpoint (single horizon) test passed!")
        return True
        
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print_error(f"Response: {e.response.text}")
        return False
    except AssertionError as e:
        print_error(f"Validation failed: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def test_error_handling() -> bool:
    """Test error handling with invalid requests."""
    print_test("Error Handling Tests")
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Invalid hospital ID
    total_tests += 1
    try:
        payload = {"hospital_ids": [99999]}  # Non-existent hospital
        response = requests.post(
            f"{BASE_URL}/predict",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        # Should either succeed with empty results or return an error
        if response.status_code in [200, 400, 404]:
            print_success("Invalid hospital ID handled correctly")
            tests_passed += 1
        else:
            print_error(f"Unexpected status code: {response.status_code}")
    except Exception as e:
        print_error(f"Error handling test failed: {e}")
    
    # Test 2: Invalid horizon
    total_tests += 1
    try:
        payload = {"horizons": [-1, 0, 100]}  # Invalid horizons
        response = requests.post(
            f"{BASE_URL}/predict",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        # Should either succeed with valid horizons or return an error
        if response.status_code in [200, 400]:
            print_success("Invalid horizons handled correctly")
            tests_passed += 1
        else:
            print_error(f"Unexpected status code: {response.status_code}")
    except Exception as e:
        print_error(f"Error handling test failed: {e}")
    
    print_info(f"Error handling tests: {tests_passed}/{total_tests} passed")
    return tests_passed == total_tests


def run_all_tests():
    """Run all API tests."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'#'*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}Hospital Forecast API Test Suite{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}Testing: {BASE_URL}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'#'*60}{Colors.RESET}\n")
    
    results = []
    hospital_ids = []
    
    # Run tests in sequence
    results.append(("Root Endpoint", test_root_endpoint()))
    results.append(("Health Check", test_health_endpoint()))
    
    success, hospitals = test_hospitals_endpoint()
    results.append(("List Hospitals", success))
    if success:
        hospital_ids = hospitals
    
    results.append(("Predict (Default)", test_predict_endpoint_default()))
    
    if hospital_ids:
        results.append(("Predict (Specific Hospitals)", 
                        test_predict_endpoint_specific_hospitals(hospital_ids)))
        results.append(("Predict (Single Horizon)", 
                        test_predict_endpoint_single_horizon(hospital_ids)))
    
    results.append(("Error Handling", test_error_handling()))
    
    # Print summary
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}Test Summary{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.GREEN}PASSED{Colors.RESET}" if result else f"{Colors.RED}FAILED{Colors.RESET}"
        print(f"{test_name:.<40} {status}")
    
    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.RESET}\n")
    
    if passed == total:
        print_success("All tests passed! 🎉")
        return 0
    else:
        print_error(f"{total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    import sys
    try:
        exit_code = run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_error("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

