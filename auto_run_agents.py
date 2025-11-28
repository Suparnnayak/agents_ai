"""
Fully Automated Agent Pipeline Runner

This script:
1. Fetches current data (or uses provided data source)
2. Calls ML prediction API
3. Runs all agents
4. Saves results
5. Sends notifications (optional)

Runs completely automatically - no manual intervention needed!
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import sys

# Configuration from environment variables
AGENT_API_URL = os.getenv(
    "AGENT_API_URL",
    "https://agents-ai-hfpb.onrender.com/agents/run"
)
ML_API_URL = os.getenv(
    "ML_API_URL",
    "https://ai-health-agent-vuol.onrender.com/predict"
)
HOSPITAL_ID = os.getenv("HOSPITAL_ID", "HOSP-123")
DISEASE_SENSITIVITY = float(os.getenv("DISEASE_SENSITIVITY", "0.5"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "plans")
NOTIFICATION_WEBHOOK = os.getenv("NOTIFICATION_WEBHOOK", "")  # Optional: Slack/Discord webhook
DATA_SOURCE = os.getenv("DATA_SOURCE", "sample")  # "sample", "api", "file"


def get_current_date() -> str:
    """Get today's date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")


def get_tomorrow_date() -> str:
    """Get tomorrow's date for forecasting."""
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


def fetch_data_from_api(api_url: str) -> Optional[List[Dict[str, Any]]]:
    """Fetch current data from an external API."""
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Handle different API response formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "data" in data:
            return data["data"]
        elif isinstance(data, dict) and "records" in data:
            return data["records"]
        else:
            print(f"⚠️  Unknown API response format: {type(data)}")
            return None
    except Exception as e:
        print(f"❌ Failed to fetch data from API: {e}")
        return None


def load_data_from_file(file_path: str) -> Optional[List[Dict[str, Any]]]:
    """Load data from a JSON file."""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "data" in data:
            return data["data"]
        else:
            return [data]  # Single record
    except Exception as e:
        print(f"❌ Failed to load data from file: {e}")
        return None


def generate_sample_data() -> List[Dict[str, Any]]:
    """Generate sample data for today/tomorrow."""
    tomorrow = get_tomorrow_date()
    
    # Get current weekday (0=Monday, 6=Sunday)
    weekday = datetime.now().weekday()
    is_weekend = 1 if weekday >= 5 else 0
    
    # Sample data - you can customize this
    return [{
        "date": tomorrow,
        "admissions": 150,  # Current day's admissions (for lag features)
        "aqi": 180,
        "temp": 28.5,
        "humidity": 65,
        "rainfall": 12.3,
        "wind_speed": 15.2,
        "mobility_index": 75,
        "outbreak_index": 30,
        "festival_flag": 0,
        "holiday_flag": 0,
        "weekday": weekday,
        "is_weekend": is_weekend,
        "population_density": 12000,
        "hospital_beds": 500,
        "staff_count": 200,
        "city_id": 1,
        "hospital_id_enc": 101
    }]


def get_input_data() -> Optional[List[Dict[str, Any]]]:
    """Get input data based on DATA_SOURCE configuration."""
    print(f"📊 Data source: {DATA_SOURCE}")
    
    if DATA_SOURCE == "api":
        api_url = os.getenv("DATA_API_URL", "")
        if not api_url:
            print("⚠️  DATA_API_URL not set, falling back to sample data")
            return generate_sample_data()
        return fetch_data_from_api(api_url)
    
    elif DATA_SOURCE == "file":
        file_path = os.getenv("DATA_FILE_PATH", "samples/sample_request.json")
        data = load_data_from_file(file_path)
        if data:
            # Update date to tomorrow for forecasting
            for record in data:
                if "date" in record:
                    record["date"] = get_tomorrow_date()
            return data
        return generate_sample_data()
    
    else:  # "sample" or default
        return generate_sample_data()


def call_agent_api(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Call the agent API and return the result."""
    try:
        print(f"🚀 Calling agent API: {AGENT_API_URL}")
        response = requests.post(
            AGENT_API_URL,
            json=payload,
            timeout=180,  # 3 minutes timeout
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print(f"❌ API request timed out after 180 seconds")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"❌ API returned error: {e.response.status_code}")
        print(f"   Response: {e.response.text[:200]}")
        return None
    except Exception as e:
        print(f"❌ Failed to call API: {e}")
        return None


def save_result(result: Dict[str, Any], output_dir: str) -> str:
    """Save the result to a JSON file."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plan = result.get("plan", {})
    request_id = plan.get("requestId", timestamp)
    filename = f"{output_dir}/plan_{request_id}_{timestamp}.json"
    
    with open(filename, "w") as f:
        json.dump(result, f, indent=2)
    
    return filename


def send_notification(result: Dict[str, Any], webhook_url: str) -> bool:
    """Send notification to Slack/Discord webhook (optional)."""
    if not webhook_url:
        return False
    
    try:
        plan = result.get("plan", {})
        alert_level = plan.get("monitorReport", {}).get("alertLevel", "unknown")
        predicted_inflow = plan.get("predictedInflow", "N/A")
        hospital_id = plan.get("hospitalId", "N/A")
        
        message = {
            "text": f"🏥 Hospital Agent Pipeline Completed",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🏥 Hospital Agent Pipeline - {hospital_id}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Alert Level:*\n{alert_level.upper()}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Predicted Inflow:*\n{predicted_inflow}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Hospital:*\n{hospital_id}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Time:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(webhook_url, json=message, timeout=10)
        response.raise_for_status()
        print(f"📧 Notification sent successfully")
        return True
    except Exception as e:
        print(f"⚠️  Failed to send notification: {e}")
        return False


def main() -> int:
    """Main automation function. Returns 0 on success, 1 on failure."""
    print("=" * 60)
    print(f"🤖 Starting FULLY AUTOMATED Agent Pipeline")
    print(f"   Time: {datetime.now().isoformat()}")
    print(f"   Hospital: {HOSPITAL_ID}")
    print("=" * 60)
    
    try:
        # Step 1: Get input data
        print("\n📊 Step 1: Fetching input data...")
        input_data = get_input_data()
        
        if not input_data:
            print("❌ Failed to get input data")
            return 1
        
        print(f"✅ Loaded {len(input_data)} record(s)")
        
        # Step 2: Prepare payload
        print("\n📦 Step 2: Preparing payload...")
        payload = {
            "data": input_data,
            "hospital_id": HOSPITAL_ID,
            "disease_sensitivity": DISEASE_SENSITIVITY,
            "mode": "ensemble"
        }
        
        # Step 3: Call agent API
        print("\n🚀 Step 3: Running agent pipeline...")
        result = call_agent_api(payload)
        
        if not result:
            print("❌ Agent pipeline failed")
            return 1
        
        # Step 4: Save result
        print("\n💾 Step 4: Saving results...")
        filename = save_result(result, OUTPUT_DIR)
        print(f"✅ Saved to: {filename}")
        
        # Step 5: Print summary
        plan = result.get("plan", {})
        print("\n" + "=" * 60)
        print("✅ SUCCESS! Agent Pipeline Completed")
        print("=" * 60)
        print(f"   Request ID: {plan.get('requestId', 'N/A')}")
        print(f"   Hospital: {plan.get('hospitalId', 'N/A')}")
        print(f"   Predicted Inflow: {plan.get('predictedInflow', 'N/A')}")
        print(f"   Alert Level: {plan.get('monitorReport', {}).get('alertLevel', 'N/A')}")
        print(f"   Doctors Needed: {plan.get('staffingPlan', {}).get('doctorsNeeded', 'N/A')}")
        print(f"   Nurses Needed: {plan.get('staffingPlan', {}).get('nursesNeeded', 'N/A')}")
        print(f"   Saved to: {filename}")
        print("=" * 60)
        
        # Step 6: Send notification (optional)
        if NOTIFICATION_WEBHOOK:
            print("\n📧 Step 5: Sending notification...")
            send_notification(result, NOTIFICATION_WEBHOOK)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

