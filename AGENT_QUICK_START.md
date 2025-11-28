# 🚀 Agent API - Quick Start Guide

## What You Get

A REST API that runs your 4 agents (Monitor, Staffing, Supplies, Advisory) and returns operational plans.

## 🎯 5-Minute Deployment

### Step 1: Choose Platform

**Option A: Railway (Recommended - Free, No Spin-Downs)**
1. Go to https://railway.app
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repo
5. Railway auto-detects and deploys!

**Option B: Render (Free Tier)**
1. Go to https://render.com
2. Connect GitHub repo
3. Create new Web Service
4. Use `render_agents.yaml` config
5. Deploy!

### Step 2: Set Environment Variables

In your deployment platform, set:

```bash
AGENT_PREDICTION_API_URL=https://ai-health-agent-vuol.onrender.com/predict
AGENT_OLLAMA_BASE_URL=http://localhost:11434  # Or cloud Ollama URL
AGENT_OLLAMA_MODEL=phi3
AGENT_TEMPERATURE=0.1
```

**For Cloud LLM (No Ollama needed):**
```bash
OPENAI_API_KEY=sk-...  # Or use Together.ai
AGENT_OLLAMA_BASE_URL=  # Leave empty if using cloud LLM
```

### Step 3: Test Your API

```bash
# Get your API URL (e.g., https://your-app.railway.app)

# Test health
curl https://your-app.railway.app/agents/health

# Test full pipeline
curl -X POST https://your-app.railway.app/agents/run \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```

---

## 📡 API Endpoints

### 1. Complete Pipeline
```bash
POST /agents/run
```
Runs all 4 agents and returns operational plan.

**Request:**
```json
{
  "data": [{
    "date": "2025-12-05",
    "admissions": 210,
    "aqi": 240,
    "temp": 26.0,
    ...
  }],
  "hospital_id": "HOSP-123",
  "disease_sensitivity": 0.5,
  "mode": "ensemble"
}
```

**Response:**
```json
{
  "status": "success",
  "plan": {
    "requestId": "...",
    "predictedInflow": 250.5,
    "monitorReport": {...},
    "staffingPlan": {...},
    "suppliesPlan": {...},
    "advisory": {...},
    "recommendedActions": [...]
  }
}
```

### 2. Individual Agents

```bash
POST /agents/monitor      # Monitor agent only
POST /agents/staffing     # Staffing planner only
POST /agents/supplies     # Supplies planner only
POST /agents/advisory     # Advisory agent only
GET  /agents/health       # Health check
GET  /agents              # API documentation
```

---

## ⚙️ Automation

### Option 1: GitHub Actions (Free)

1. **Add secrets to GitHub:**
   - Go to repo → Settings → Secrets
   - Add `AGENT_API_URL` = `https://your-app.railway.app/agents/run`

2. **Workflow is already created** (`.github/workflows/run_agents.yml`)
   - Runs daily at 8 AM UTC
   - Can trigger manually from Actions tab

3. **Done!** ✅

### Option 2: Python Script (Any Platform)

```bash
# Set environment variables
export AGENT_API_URL=https://your-app.railway.app/agents/run
export HOSPITAL_ID=HOSP-123

# Run
python automate_agents.py
```

**Schedule with cron:**
```bash
# Edit crontab
crontab -e

# Add line (runs daily at 8 AM)
0 8 * * * cd /path/to/project && python automate_agents.py
```

### Option 3: Zapier / Make.com (No Code)

1. **Zapier:**
   - Trigger: Schedule (Daily)
   - Action: Webhook (POST to `/agents/run`)
   - Action: Save to Google Sheets

2. **Make.com:**
   - Schedule trigger
   - HTTP request to agent API
   - Save to database

---

## 🔧 Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AGENT_PREDICTION_API_URL=https://ai-health-agent-vuol.onrender.com/predict
export AGENT_OLLAMA_BASE_URL=http://localhost:11434

# Start Ollama (if using local)
ollama serve
ollama pull phi3

# Start agent API
python agent_api_server.py

# Test
curl http://localhost:5001/agents/health
```

---

## 🐛 Troubleshooting

### "Ollama connection failed"
- **Local:** Make sure `ollama serve` is running
- **Cloud:** Set `AGENT_OLLAMA_BASE_URL` to your cloud Ollama URL
- **Alternative:** Use cloud LLM (OpenAI/Together.ai) instead

### "Prediction API timeout"
- Your prediction API may be sleeping (Render free tier)
- Use UptimeRobot to keep it alive
- Or upgrade to paid tier

### "Agent API not responding"
- Check health endpoint: `/agents/health`
- Check logs in deployment platform
- Verify environment variables are set

---

## 📊 Example Usage

### Python Client

```python
import requests

API_URL = "https://your-app.railway.app/agents/run"

payload = {
    "data": [{
        "date": "2025-12-05",
        "admissions": 210,
        "aqi": 240,
        "temp": 26.0,
        # ... other fields
    }],
    "hospital_id": "HOSP-123",
    "disease_sensitivity": 0.5
}

response = requests.post(API_URL, json=payload)
plan = response.json()["plan"]

print(f"Predicted Inflow: {plan['predictedInflow']}")
print(f"Alert Level: {plan['monitorReport']['alertLevel']}")
print(f"Doctors Needed: {plan['staffingPlan']['doctorsNeeded']}")
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

const API_URL = 'https://your-app.railway.app/agents/run';

const payload = {
  data: [{
    date: '2025-12-05',
    admissions: 210,
    aqi: 240,
    temp: 26.0,
    // ... other fields
  }],
  hospital_id: 'HOSP-123',
  disease_sensitivity: 0.5
};

axios.post(API_URL, payload)
  .then(response => {
    const plan = response.data.plan;
    console.log('Predicted Inflow:', plan.predictedInflow);
    console.log('Alert Level:', plan.monitorReport.alertLevel);
  })
  .catch(error => console.error('Error:', error));
```

---

## 🎯 Next Steps

1. ✅ Deploy agent API (Railway/Render)
2. ✅ Test with sample data
3. ✅ Set up automation (GitHub Actions/Zapier)
4. ✅ Integrate with your hospital system
5. ✅ Monitor and optimize

---

## 💡 Pro Tips

- **Use Railway** for free tier with no spin-downs
- **Use Together.ai** for cheap cloud LLMs ($0.0001/request)
- **Set up UptimeRobot** to keep prediction API alive
- **Use GitHub Actions** for free automation
- **Save results** to database/notifications for tracking

---

## 📚 Full Documentation

See `AGENT_DEPLOYMENT_GUIDE.md` for detailed deployment options and advanced configuration.

