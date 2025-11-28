# 🚀 Deployment Solutions for Always-On API

## Problem: Render Free Tier Spins Down
Render's free tier automatically spins down services after ~15 minutes of inactivity, causing:
- Cold starts (30-60 seconds)
- Timeout errors
- Poor user experience

## ✅ Solution 1: Keep-Alive Service (Free)

### Option A: External Keep-Alive Service
Use a free service to ping your API every 10 minutes:

**Services:**
- **UptimeRobot** (free): https://uptimerobot.com
- **Cronitor** (free tier): https://cronitor.io
- **Pingdom** (free tier): https://www.pingdom.com

**Setup:**
1. Sign up for UptimeRobot (free)
2. Add a new monitor:
   - URL: `https://ai-health-agent-vuol.onrender.com/health`
   - Type: HTTP(s)
   - Interval: 5 minutes
3. Save - it will ping your API every 5 minutes

### Option B: Self-Hosted Keep-Alive Script
Create a simple script that runs on your local machine or a free service:

```python
# keep_alive.py
import requests
import time
from datetime import datetime

API_URL = "https://ai-health-agent-vuol.onrender.com/health"

def ping_api():
    try:
        response = requests.get(API_URL, timeout=10)
        if response.status_code == 200:
            print(f"✅ {datetime.now()}: API is alive")
        else:
            print(f"⚠️  {datetime.now()}: API returned {response.status_code}")
    except Exception as e:
        print(f"❌ {datetime.now()}: Error - {e}")

if __name__ == "__main__":
    while True:
        ping_api()
        time.sleep(300)  # Ping every 5 minutes
```

Run it:
```bash
# Install requests
pip install requests

# Run in background (Linux/Mac)
nohup python keep_alive.py &

# Or use Windows Task Scheduler to run every 5 minutes
```

---

## ✅ Solution 2: Upgrade Render Plan (Recommended)

### Render Starter Plan ($7/month)
- **No spin-downs** - Always running
- 512 MB RAM
- 0.5 CPU
- Perfect for production

**Steps:**
1. Go to Render Dashboard
2. Select your service
3. Click "Settings" → "Plan"
4. Upgrade to "Starter" ($7/month)

**Update `render.yaml`:**
```yaml
services:
  - type: web
    name: hospital-forecast-api
    plan: starter  # Changed from free tier
    # ... rest of config
```

---

## ✅ Solution 3: Switch to Railway (Free Tier - No Spin-Downs)

Railway's free tier doesn't spin down services (with usage limits).

### Setup:
1. Sign up: https://railway.app
2. Connect your GitHub repo
3. Deploy automatically

**Create `railway.json`:**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python api_server.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Environment Variables:**
- `PORT` (auto-set by Railway)
- `PREDICTION_MODE=ensemble`
- `TFT_WEIGHT=0.6`

---

## ✅ Solution 4: Fly.io (Free Tier - No Spin-Downs)

Fly.io offers a generous free tier with no spin-downs.

### Setup:
1. Install Fly CLI: https://fly.io/docs/getting-started/installing-flyctl/
2. Sign up: `fly auth signup`
3. Create `fly.toml`:

```toml
app = "hospital-forecast-api"
primary_region = "iad"

[build]

[http_service]
  internal_port = 5000
  force_https = true
  auto_stop_machines = false  # Keep alive!
  auto_start_machines = true
  min_machines_running = 1

[[services]]
  protocol = "tcp"
  internal_port = 5000

  [[services.ports]]
    port = 80
    handlers = ["http"]
    force_https = true

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
```

4. Deploy: `fly deploy`

---

## ✅ Solution 5: Render with Better Configuration

Even on free tier, optimize your setup:

### Update `api_server.py` - Add Warmup Endpoint
```python
@app.route("/warmup", methods=["GET"])
def warmup():
    """Warmup endpoint to preload models."""
    try:
        # Preload models on first request
        from src.pipeline.ensemble_predictor import _load_models
        _load_models()
        return jsonify({"status": "warmed_up"})
    except:
        return jsonify({"status": "warmup_failed"}), 500
```

### Use Gunicorn for Better Performance
Update `Procfile`:
```
web: gunicorn -w 2 -b 0.0.0.0:$PORT --timeout 120 api_server:app
```

Update `requirements.txt`:
```
gunicorn>=21.2.0
```

---

## ✅ Solution 6: Cloud Run (Google Cloud - Pay Per Use)

Google Cloud Run only charges when handling requests (very cheap).

### Setup:
1. Install gcloud CLI
2. Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 api_server:app
```

3. Deploy:
```bash
gcloud run deploy hospital-forecast \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 1  # Keep 1 instance always running
```

**Cost:** ~$0.10/month for always-on instance

---

## 🎯 Recommended Approach

**For Development/Testing:**
- Use **UptimeRobot** (Solution 1A) - Free and easy

**For Production:**
- **Option A**: Upgrade Render to Starter ($7/month)
- **Option B**: Switch to Railway (free tier, no spin-downs)
- **Option C**: Use Fly.io (free tier, no spin-downs)

**For Enterprise:**
- Google Cloud Run with min-instances=1
- AWS ECS Fargate
- Azure Container Instances

---

## 📊 Comparison

| Platform | Free Tier | Spin-Down | Always-On Cost |
|----------|-----------|-----------|----------------|
| Render | ✅ | ❌ Yes | $7/month |
| Railway | ✅ | ✅ No | Free (with limits) |
| Fly.io | ✅ | ✅ No | Free (with limits) |
| Cloud Run | ✅ | ✅ No | ~$0.10/month |
| Heroku | ❌ | ❌ Yes | $7/month |

---

## 🚀 Quick Start: Keep-Alive (5 minutes)

1. Go to https://uptimerobot.com
2. Sign up (free)
3. Add Monitor:
   - URL: `https://ai-health-agent-vuol.onrender.com/health`
   - Interval: 5 minutes
4. Done! Your API stays alive.

---

## 🔧 Update Your Agent Client

Your `agents/prediction_client.py` already has retry logic, but you can add a pre-wakeup call:

```python
def predict(self, payload: Dict[str, Any]) -> float:
    # Wake up service first
    self._wake_up_service(str(self.settings.prediction_api_url))
    # ... rest of code
```

This is already implemented! ✅

