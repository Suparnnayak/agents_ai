# 🚀 Agent Deployment Guide

## Overview
Deploy your agent system as a REST API that can be called from anywhere and automated.

## Architecture

```
┌─────────────────┐
│  Agent API      │  (This service - agent_api_server.py)
│  Port: 5001     │
└────────┬────────┘
         │
         ├──→ Ollama (LLM) - Can be local or cloud
         │
         └──→ Prediction API (ML Model) - https://ai-health-agent-vuol.onrender.com
```

## 🎯 Deployment Options

### Option 1: Render (Recommended for Free Tier)

**Pros:**
- Free tier available
- Easy GitHub integration
- Auto-deploy on push

**Cons:**
- Spins down after inactivity (use UptimeRobot to keep alive)

**Setup:**

1. **Create `render_agents.yaml`:**
```yaml
services:
  - type: web
    name: hospital-agent-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python agent_api_server.py
    envVars:
      - key: PORT
        value: 10000
      - key: HOST
        value: 0.0.0.0
      - key: AGENT_PREDICTION_API_URL
        value: https://ai-health-agent-vuol.onrender.com/predict
      - key: AGENT_OLLAMA_BASE_URL
        value: http://localhost:11434  # Or use cloud Ollama
      - key: AGENT_OLLAMA_MODEL
        value: phi3
    healthCheckPath: /agents/health
    plan: starter  # Or free
```

2. **Deploy:**
   - Push to GitHub
   - Connect repo to Render
   - Render will auto-deploy

3. **Keep Alive:**
   - Use UptimeRobot to ping `/agents/health` every 5 minutes

---

### Option 2: Railway (Best for Free Tier - No Spin-Downs)

**Pros:**
- Free tier with no spin-downs
- Easy deployment
- Great for automation

**Setup:**

1. **Create `railway.json`:**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python agent_api_server.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

2. **Deploy:**
   - Sign up: https://railway.app
   - Connect GitHub repo
   - Railway auto-detects and deploys

3. **Environment Variables:**
   - `PORT` (auto-set)
   - `AGENT_PREDICTION_API_URL=https://ai-health-agent-vuol.onrender.com/predict`
   - `AGENT_OLLAMA_BASE_URL=http://localhost:11434` (or cloud URL)
   - `AGENT_OLLAMA_MODEL=phi3`

---

### Option 3: Fly.io (Free Tier - No Spin-Downs)

**Setup:**

1. **Create `fly.toml`:**
```toml
app = "hospital-agent-api"
primary_region = "iad"

[build]

[http_service]
  internal_port = 5001
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1

[[services]]
  protocol = "tcp"
  internal_port = 5001

  [[services.ports]]
    port = 80
    handlers = ["http"]
    force_https = true

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

[env]
  AGENT_PREDICTION_API_URL = "https://ai-health-agent-vuol.onrender.com/predict"
  AGENT_OLLAMA_BASE_URL = "http://localhost:11434"
  AGENT_OLLAMA_MODEL = "phi3"
```

2. **Deploy:**
```bash
fly launch
fly deploy
```

---

## 🤖 Ollama Setup Options

### Option A: Deploy Ollama Separately (Recommended)

**Deploy Ollama on Render/Railway:**

1. **Create `ollama_service.yaml`:**
```yaml
services:
  - type: web
    name: ollama-service
    env: docker
    dockerfilePath: ./Dockerfile.ollama
    envVars:
      - key: OLLAMA_HOST
        value: 0.0.0.0
    plan: starter  # Needs more resources
```

2. **Create `Dockerfile.ollama`:**
```dockerfile
FROM ollama/ollama:latest
EXPOSE 11434
CMD ["ollama", "serve"]
```

3. **Pull model:**
```bash
# After deployment, SSH into service and run:
ollama pull phi3
```

4. **Update agent config:**
```bash
AGENT_OLLAMA_BASE_URL=https://your-ollama-service.onrender.com
```

### Option B: Use Cloud LLM Services

**Replace Ollama with OpenAI/Anthropic:**

Update `agents/llm_client.py` to use OpenAI instead:

```python
from langchain_openai import ChatOpenAI

class LLMClient:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
```

**Cost:** ~$0.002 per request (very cheap for structured outputs)

### Option C: Use Together.ai (Cheap Cloud LLMs)

**Setup:**
1. Sign up: https://together.ai
2. Get API key
3. Update `llm_client.py`:

```python
from langchain_together import Together

self.llm = Together(
    model="meta-llama/Llama-3-8b-chat-hf",
    together_api_key=os.getenv("TOGETHER_API_KEY"),
    temperature=0.1
)
```

**Cost:** ~$0.0001 per request

---

## 📡 API Usage

### Complete Pipeline

```bash
curl -X POST https://your-agent-api.onrender.com/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "data": [{
      "date": "2025-12-05",
      "admissions": 210,
      "aqi": 240,
      "temp": 26.0,
      "humidity": 70,
      "rainfall": 5.0,
      "wind_speed": 9.0,
      "mobility_index": 65,
      "outbreak_index": 45,
      "festival_flag": 1,
      "holiday_flag": 0,
      "weekday": 5,
      "is_weekend": 1,
      "population_density": 15000,
      "hospital_beds": 650,
      "staff_count": 280,
      "city_id": 2,
      "hospital_id_enc": 222
    }],
    "hospital_id": "HOSP-123",
    "disease_sensitivity": 0.5,
    "mode": "ensemble"
  }'
```

### Individual Agents

```bash
# Monitor only
curl -X POST https://your-agent-api.onrender.com/agents/monitor \
  -H "Content-Type: application/json" \
  -d '{
    "aqi": 240,
    "festival_score": 1.0,
    "weather_risk": 0.3,
    "disease_sensitivity": 0.5
  }'

# Staffing only
curl -X POST https://your-agent-api.onrender.com/agents/staffing \
  -H "Content-Type: application/json" \
  -d '{"predicted_inflow": 250}'

# Supplies only
curl -X POST https://your-agent-api.onrender.com/agents/supplies \
  -H "Content-Type: application/json" \
  -d '{"predicted_inflow": 250}'
```

---

## ⚙️ Automation Options

### Option 1: Cron Job / Scheduled Task

**Using PythonAnywhere (Free):**

1. Sign up: https://www.pythonanywhere.com
2. Upload automation script
3. Schedule to run daily/hourly

**Create `automate_agents.py`:**
```python
import requests
import json
from datetime import datetime

AGENT_API_URL = "https://your-agent-api.onrender.com/agents/run"

# Load your data
with open("samples/sample_request.json") as f:
    payload = json.load(f)

# Add hospital ID
payload["hospital_id"] = "HOSP-123"
payload["disease_sensitivity"] = 0.5

# Call API
response = requests.post(AGENT_API_URL, json=payload)
result = response.json()

# Save result
with open(f"plans/plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
    json.dump(result, f, indent=2)

print("✅ Plan generated:", result["plan"]["requestId"])
```

**Schedule:**
- PythonAnywhere: Tasks → Add new task → Run daily at 8 AM

---

### Option 2: GitHub Actions (Free)

**Create `.github/workflows/run_agents.yml`:**
```yaml
name: Run Agents Daily

on:
  schedule:
    - cron: '0 8 * * *'  # 8 AM daily
  workflow_dispatch:  # Manual trigger

jobs:
  run-agents:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install requests
      
      - name: Run agents
        env:
          AGENT_API_URL: ${{ secrets.AGENT_API_URL }}
        run: |
          python automate_agents.py
      
      - name: Commit results
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add plans/
          git commit -m "Auto-generated plan $(date)" || exit 0
          git push
```

---

### Option 3: Zapier / Make.com (No Code)

**Zapier Setup:**
1. Sign up: https://zapier.com
2. Create Zap:
   - Trigger: Schedule (Daily at 8 AM)
   - Action: Webhook (POST to your agent API)
   - Action: Save to Google Sheets / Notion

**Make.com Setup:**
1. Sign up: https://make.com
2. Create scenario:
   - Schedule trigger
   - HTTP request to agent API
   - Save to database/email

---

### Option 4: Render Cron Jobs

**Create `render_cron.yaml`:**
```yaml
services:
  - type: cron
    name: daily-agent-run
    schedule: "0 8 * * *"  # 8 AM daily
    buildCommand: pip install -r requirements.txt
    runCommand: python automate_agents.py
    envVars:
      - key: AGENT_API_URL
        value: https://your-agent-api.onrender.com/agents/run
```

---

## 🔧 Environment Variables

Create `.env` file or set in deployment platform:

```bash
# Agent API
PORT=5001
HOST=0.0.0.0

# Prediction API
AGENT_PREDICTION_API_URL=https://ai-health-agent-vuol.onrender.com/predict

# Ollama (choose one)
AGENT_OLLAMA_BASE_URL=http://localhost:11434
# OR
AGENT_OLLAMA_BASE_URL=https://your-ollama-service.onrender.com

AGENT_OLLAMA_MODEL=phi3
AGENT_TEMPERATURE=0.1

# Alternative: Cloud LLM
# OPENAI_API_KEY=sk-...
# TOGETHER_API_KEY=...
```

---

## 📊 Testing

### Local Testing

```bash
# Start agent API
python agent_api_server.py

# Test health
curl http://localhost:5001/agents/health

# Test full pipeline
curl -X POST http://localhost:5001/agents/run \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```

### Production Testing

```bash
# Test deployed API
curl https://your-agent-api.onrender.com/agents/health

# Test with your data
curl -X POST https://your-agent-api.onrender.com/agents/run \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```

---

## 🎯 Quick Start (5 Minutes)

1. **Deploy to Railway:**
   ```bash
   # Push to GitHub
   git add agent_api_server.py
   git commit -m "Add agent API"
   git push
   
   # Go to railway.app, connect repo, deploy
   ```

2. **Set Environment Variables:**
   - `AGENT_PREDICTION_API_URL`
   - `AGENT_OLLAMA_BASE_URL` (or use cloud LLM)

3. **Test:**
   ```bash
   curl https://your-app.railway.app/agents/health
   ```

4. **Automate:**
   - Use Zapier/Make.com to call API daily
   - Or use GitHub Actions

---

## 💰 Cost Comparison

| Solution | Cost | Spin-Down | Ollama Support |
|----------|------|-----------|----------------|
| Render Free | $0 | Yes | Limited |
| Render Starter | $7/mo | No | Yes |
| Railway Free | $0 | No | Yes |
| Fly.io Free | $0 | No | Yes |
| Cloud LLM | ~$0.01/req | N/A | N/A |

**Recommendation:** Railway (free) + Together.ai ($0.0001/request) = ~$0.01/month

