"""
Automation script to call the Agent API on a schedule.

Usage:
    python automate_agents.py

Can be run via:
    - Cron jobs (Linux/Mac)
    - Task Scheduler (Windows)
    - GitHub Actions
    - PythonAnywhere scheduled tasks
    - Zapier/Make.com webhooks
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configuration
AGENT_API_URL = os.getenv(
    "AGENT_API_URL",
    "https://your-agent-api.onrender.com/agents/run"
)
PAYLOAD_FILE = os.getenv("PAYLOAD_FILE", "samples/sample_request.json")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "plans")
HOSPITAL_ID = os.getenv("HOSPITAL_ID", "HOSP-123")
DISEASE_SENSITIVITY = float(os.getenv("DISEASE_SENSITIVITY", "0.5"))


def load_payload(file_path: str) -> dict:
    """Load payload from JSON file."""
    with open(file_path, "r") as f:
        payload = json.load(f)
    return payload


def call_agent_api(payload: dict) -> dict:
    """Call the agent API and return the result."""
    try:
        response = requests.post(
            AGENT_API_URL,
            json=payload,
            timeout=120,  # 2 minutes timeout
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise Exception(f"API request timed out after 120 seconds")
    except requests.exceptions.HTTPError as e:
        raise Exception(f"API returned error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Failed to call API: {e}")


def save_result(result: dict, output_dir: str) -> str:
    """Save the result to a JSON file."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    request_id = result.get("plan", {}).get("requestId", timestamp)
    filename = f"{output_dir}/plan_{request_id}_{timestamp}.json"
    
    with open(filename, "w") as f:
        json.dump(result, f, indent=2)
    
    return filename


def main():
    """Main automation function."""
    print(f"🤖 Starting agent automation at {datetime.now().isoformat()}")
    print(f"📡 Agent API: {AGENT_API_URL}")
    print(f"📄 Payload file: {PAYLOAD_FILE}")
    
    try:
        # Load payload
        print(f"📖 Loading payload from {PAYLOAD_FILE}...")
        payload = load_payload(PAYLOAD_FILE)
        
        # Add metadata
        payload["hospital_id"] = HOSPITAL_ID
        payload["disease_sensitivity"] = DISEASE_SENSITIVITY
        payload.setdefault("mode", "ensemble")
        
        # Call API
        print(f"🚀 Calling agent API...")
        result = call_agent_api(payload)
        
        # Save result
        print(f"💾 Saving result...")
        filename = save_result(result, OUTPUT_DIR)
        
        # Print summary
        plan = result.get("plan", {})
        print(f"\n✅ Success!")
        print(f"   Request ID: {plan.get('requestId', 'N/A')}")
        print(f"   Hospital: {plan.get('hospitalId', 'N/A')}")
        print(f"   Predicted Inflow: {plan.get('predictedInflow', 'N/A')}")
        print(f"   Alert Level: {plan.get('monitorReport', {}).get('alertLevel', 'N/A')}")
        print(f"   Saved to: {filename}")
        
        return result
        
    except FileNotFoundError:
        print(f"❌ Error: Payload file not found: {PAYLOAD_FILE}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


if __name__ == "__main__":
    main()

