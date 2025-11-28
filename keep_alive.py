"""
Keep-Alive Script for Render API
Pings the health endpoint every 5 minutes to prevent spin-down.

Usage:
    python keep_alive.py

Or run in background:
    nohup python keep_alive.py > keep_alive.log 2>&1 &
    
Or use Windows Task Scheduler to run every 5 minutes.
"""

import requests
import time
from datetime import datetime
from typing import Optional

# Your Render API URL
API_URL = "https://ai-health-agent-vuol.onrender.com/health"

# Ping interval in seconds (5 minutes = 300 seconds)
PING_INTERVAL = 300

# Timeout for each request
REQUEST_TIMEOUT = 30


def ping_api() -> bool:
    """Ping the API health endpoint. Returns True if successful."""
    try:
        response = requests.get(API_URL, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown")
            print(f"✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: API is alive (status: {status})")
            return True
        else:
            print(f"⚠️  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: API returned {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        print(f"⏱️  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Request timed out (service may be spinning up)")
        return False
    except requests.exceptions.ConnectionError:
        print(f"🔌 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Connection error (service may be down)")
        return False
    except Exception as e:
        print(f"❌ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Error - {e}")
        return False


def main():
    """Main loop to ping API at regular intervals."""
    print(f"🚀 Keep-Alive Service Started")
    print(f"📡 Pinging: {API_URL}")
    print(f"⏰ Interval: {PING_INTERVAL} seconds ({PING_INTERVAL // 60} minutes)")
    print(f"Press Ctrl+C to stop\n")
    
    consecutive_failures = 0
    max_failures = 5
    
    try:
        while True:
            success = ping_api()
            
            if success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    print(f"\n⚠️  WARNING: {max_failures} consecutive failures. Service may be down.\n")
            
            # Wait before next ping
            time.sleep(PING_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 Keep-Alive Service Stopped")
        print(f"   Last ping: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()

