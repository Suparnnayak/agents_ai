# 🤖 Hospital Agent System - Autonomous Planning Agents

Autonomous agent system that uses ML predictions to generate operational plans for hospital resource management.

## 🎯 Overview

This system consists of **4 specialized agents** that work together to create comprehensive operational plans:

1. **Monitor Agent** - Evaluates environmental and seasonal risks (AQI, weather, festivals)
2. **Staffing Planner** - Plans doctor, nurse, and support staff requirements
3. **Supplies Planner** - Plans medical supplies (oxygen, beds, medicines)
4. **Advisory Agent** - Generates public advisories, triage rules, and clinical guidance
5. **Coordinator** - Aggregates all outputs into a final operational plan

## 🚀 Quick Start

### 1. Prerequisites

**Install Ollama:**
```bash
# Download from https://ollama.com
# Pull a model
ollama pull phi3
# Or
ollama pull llama3
```

**Install Python Dependencies:**
```bash
pip install -r requirements.txt
```

### 2. Configuration

Create `.env` file (optional):
```bash
AGENT_PREDICTION_API_URL=https://ai-health-agent-vuol.onrender.com/predict
AGENT_OLLAMA_BASE_URL=http://localhost:11434
AGENT_OLLAMA_MODEL=phi3
AGENT_TEMPERATURE=0.1
```

### 3. Run Locally

```bash
python -m agents.run_pipeline \
  --payload-file samples/sample_request.json \
  --hospital-id HOSP-123 \
  --disease-sensitivity 0.5
```

### 4. Deploy as API

```bash
python agent_api_server.py
```

Test:
```bash
curl http://localhost:5001/agents/health
```

## 📖 Usage

### Command Line Interface

```bash
# Basic usage
python -m agents.run_pipeline \
  --payload-file samples/sample_request.json \
  --hospital-id HOSP-123

# With custom disease sensitivity
python -m agents.run_pipeline \
  --payload-file samples/sample_request.json \
  --hospital-id HOSP-123 \
  --disease-sensitivity 0.7

# Save output to file
python -m agents.run_pipeline \
  --payload-file samples/sample_request.json \
  --hospital-id HOSP-123 \
  --save-artifact plans/plan_2025-12-05.json
```

### Python API

```python
from agents.run_pipeline import _derive_monitor_inputs
from agents.monitor_agent import run_monitor_agent
from agents.planning_agent import run_staffing_planner, run_supplies_planner
from agents.advisory_agent import run_advisory_agent
from agents.coordinator_agent import assemble_operational_plan
from agents.prediction_client import prediction_client
from agents.schemas import MonitorInput

# Step 1: Get prediction
payload = {
    "mode": "ensemble",
    "data": [{
        "date": "2025-12-05",
        "admissions": 210,
        "aqi": 240,
        # ... other fields
    }]
}
predicted_inflow = prediction_client.predict(payload)

# Step 2: Run agents
monitor_inputs = MonitorInput(
    aqi=240,
    festival_score=1.0,
    weather_risk=0.3,
    disease_sensitivity=0.5
)
monitor_report = run_monitor_agent(monitor_inputs)
staffing = run_staffing_planner(predicted_inflow)
supplies = run_supplies_planner(predicted_inflow)
advisory = run_advisory_agent(predicted_inflow, monitor_report)

# Step 3: Assemble plan
plan = assemble_operational_plan(
    hospital_id="HOSP-123",
    predicted_inflow=predicted_inflow,
    monitor_report=monitor_report,
    staffing=staffing,
    supplies=supplies,
    advisory=advisory,
    trace=[]
)
```

### REST API

#### Complete Pipeline
```bash
curl -X POST https://your-agent-api.railway.app/agents/run \
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

#### Individual Agents

```bash
# Monitor only
curl -X POST https://your-agent-api.railway.app/agents/monitor \
  -H "Content-Type: application/json" \
  -d '{
    "aqi": 240,
    "festival_score": 1.0,
    "weather_risk": 0.3,
    "disease_sensitivity": 0.5
  }'

# Staffing only
curl -X POST https://your-agent-api.railway.app/agents/staffing \
  -H "Content-Type: application/json" \
  -d '{"predicted_inflow": 250}'

# Supplies only
curl -X POST https://your-agent-api.railway.app/agents/supplies \
  -H "Content-Type: application/json" \
  -d '{"predicted_inflow": 250}'
```

## 📊 Output Format

### Complete Operational Plan

```json
{
  "requestId": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-05T10:30:00Z",
  "hospitalId": "HOSP-123",
  "predictedInflow": 250.5,
  "monitorReport": {
    "alertLevel": "high",
    "riskFactors": [
      "AQI > 200",
      "Festival season",
      "High humidity"
    ],
    "recommendedUrgency": "activate surge"
  },
  "staffingPlan": {
    "doctorsNeeded": 45,
    "nursesNeeded": 120,
    "supportStaffNeeded": 75
  },
  "suppliesPlan": {
    "oxygenCylinders": 85,
    "beds": 280,
    "commonMedicines": [
      "Paracetamol",
      "Ibuprofen",
      "Antibiotics"
    ],
    "specialMedicines": [
      "Ventilator medications",
      "ICU sedatives"
    ]
  },
  "advisory": {
    "publicAdvisory": "High pollution levels detected. Vulnerable individuals should limit outdoor activities...",
    "triageRules": "Prioritize respiratory cases. Activate surge protocol for AQI > 200...",
    "teleconsultation": "Increase teleconsultation capacity by 30% to reduce in-person load...",
    "pollutionCare": "Ensure adequate nebulizer availability. Stock N95 masks for staff..."
  },
  "recommendedActions": [
    "Notify respiratory teams about alert level high",
    "Stage 85 oxygen cylinders near ER",
    "Activate surge bed protocol and inform city EMS",
    "Call in locum physicians for night shift coverage"
  ],
  "agentTrace": [
    {
      "agent": "prediction_api",
      "message": "Fetched predictions",
      "timestamp": "2025-12-05T10:30:00Z"
    },
    {
      "agent": "monitor",
      "message": "Alert high",
      "timestamp": "2025-12-05T10:30:01Z"
    }
  ]
}
```

## 🏗️ Architecture

```
┌─────────────────┐
│  Input Data     │  (Hospital metrics, weather, AQI, etc.)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Prediction API  │  (ML Model - returns predicted_inflow)
└────────┬────────┘
         │
         ├──→ Monitor Agent ──→ Alert Level, Risk Factors
         │
         ├──→ Staffing Planner ──→ Doctors, Nurses, Support Staff
         │
         ├──→ Supplies Planner ──→ Oxygen, Beds, Medicines
         │
         └──→ Advisory Agent ──→ Public Advisory, Triage Rules
         │
         ▼
┌─────────────────┐
│  Coordinator    │  (Assembles final operational plan)
└─────────────────┘
```

## 🔧 Configuration

### Environment Variables

```bash
# Prediction API
AGENT_PREDICTION_API_URL=https://ai-health-agent-vuol.onrender.com/predict

# Ollama Configuration
AGENT_OLLAMA_BASE_URL=http://localhost:11434
AGENT_OLLAMA_MODEL=phi3  # Options: phi3, llama3, mistral
AGENT_TEMPERATURE=0.1    # Lower = more deterministic

# Retry Settings
AGENT_MAX_RETRIES=3
```

### Using Cloud LLM (Alternative to Ollama)

Instead of local Ollama, use cloud LLM services:

**OpenAI:**
```bash
OPENAI_API_KEY=sk-...
# Update agents/llm_client.py to use ChatOpenAI
```

**Together.ai (Cheap):**
```bash
TOGETHER_API_KEY=...
# Update agents/llm_client.py to use Together
```

## 🌐 Deployment

### Railway (Recommended - Free, No Spin-Downs)

1. **Sign up:** https://railway.app
2. **Connect GitHub repo**
3. **Set environment variables:**
   - `AGENT_PREDICTION_API_URL`
   - `AGENT_OLLAMA_BASE_URL` (or use cloud LLM)
   - `AGENT_OLLAMA_MODEL`
4. **Deploy automatically**

### Render

1. **Create `render_agents.yaml`:**
```yaml
services:
  - type: web
    name: hospital-agent-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python agent_api_server.py
    envVars:
      - key: AGENT_PREDICTION_API_URL
        value: https://ai-health-agent-vuol.onrender.com/predict
    healthCheckPath: /agents/health
    plan: starter
```

2. **Deploy via Render dashboard**

### Local Development

```bash
# Start Ollama
ollama serve
ollama pull phi3

# Start agent API
python agent_api_server.py

# Test
curl http://localhost:5001/agents/health
```

## ⚙️ Automation

### GitHub Actions (Free)

Already configured in `.github/workflows/run_agents.yml`:

```yaml
# Runs daily at 8 AM UTC
on:
  schedule:
    - cron: '0 8 * * *'
```

**Setup:**
1. Add secrets to GitHub:
   - `AGENT_API_URL` = Your deployed agent API URL
   - `HOSPITAL_ID` = Your hospital ID
2. Workflow runs automatically

### Cron Job

```bash
# Edit crontab
crontab -e

# Add line (runs daily at 8 AM)
0 8 * * * cd /path/to/project && python automate_agents.py
```

### Python Script

```bash
# Set environment variables
export AGENT_API_URL=https://your-agent-api.railway.app/agents/run
export HOSPITAL_ID=HOSP-123

# Run
python automate_agents.py
```

### Zapier / Make.com (No Code)

1. **Zapier:**
   - Trigger: Schedule (Daily)
   - Action: Webhook (POST to `/agents/run`)
   - Action: Save to Google Sheets

2. **Make.com:**
   - Schedule trigger
   - HTTP request to agent API
   - Save to database

## 📁 Project Structure

```
agents/
├── __init__.py
├── config.py                    # Configuration management
├── schemas.py                   # Pydantic data models
├── llm_client.py                # Ollama/LLM integration
├── prediction_client.py         # ML API client
├── monitor_agent.py             # Monitor agent
├── planning_agent.py            # Staffing & Supplies planners
├── advisory_agent.py            # Advisory agent
├── coordinator_agent.py        # Plan coordinator
└── run_pipeline.py              # CLI entrypoint

agent_api_server.py              # REST API server
automate_agents.py               # Automation script
samples/
└── sample_request.json          # Example input
```

## 🧪 Testing

### Test Locally

```bash
# Test CLI
python -m agents.run_pipeline \
  --payload-file samples/sample_request.json \
  --hospital-id HOSP-123

# Test API
python agent_api_server.py
curl http://localhost:5001/agents/health
```

### Test Individual Agents

```python
from agents.monitor_agent import run_monitor_agent
from agents.schemas import MonitorInput

inputs = MonitorInput(
    aqi=240,
    festival_score=1.0,
    weather_risk=0.3,
    disease_sensitivity=0.5
)

result = run_monitor_agent(inputs)
print(result.alertLevel)  # "high"
```

## 🐛 Troubleshooting

### Ollama Connection Failed
```
Error: Connection refused to http://localhost:11434
```
**Solution:**
- Start Ollama: `ollama serve`
- Check `AGENT_OLLAMA_BASE_URL` environment variable
- Or use cloud LLM instead

### Prediction API Timeout
```
ReadTimeout: The read operation timed out
```
**Solution:**
- Prediction API may be sleeping (Render free tier)
- Use UptimeRobot to keep it alive
- Or upgrade to paid tier

### LLM Output Parsing Error
```
OutputParserException: Failed to parse JSON
```
**Solution:**
- JSON repair logic is already implemented
- Try a different model (e.g., `llama3` instead of `phi3`)
- Lower temperature: `AGENT_TEMPERATURE=0.1`

### Missing Dependencies
```
ModuleNotFoundError: No module named 'langchain'
```
**Solution:**
```bash
pip install -r requirements.txt
```

## 🔄 Customization

### Change LLM Model

```bash
# In .env or environment variables
AGENT_OLLAMA_MODEL=llama3  # or mistral, phi3, etc.
```

### Modify Agent Prompts

Edit prompt templates in:
- `agents/monitor_agent.py` - Monitor agent prompt
- `agents/planning_agent.py` - Staffing/Supplies prompts
- `agents/advisory_agent.py` - Advisory prompt

### Adjust Output Schemas

Modify Pydantic models in `agents/schemas.py`:
- `MonitorOutput`
- `StaffingPlan`
- `SuppliesPlan`
- `AdvisoryOutput`

## 📚 Additional Documentation

- `AGENT_DEPLOYMENT_GUIDE.md` - Detailed deployment guide
- `AGENT_QUICK_START.md` - Quick start guide
- `AGENT_DATA_FLOW.md` - Data flow documentation

## 💡 Best Practices

1. **Use Cloud LLM** for production (Together.ai is very cheap)
2. **Monitor API health** with UptimeRobot
3. **Save plans** to database for tracking
4. **Set up alerts** for high alert levels
5. **Automate daily runs** with GitHub Actions or cron

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Test thoroughly with different scenarios
4. Submit pull request

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

- Ollama team for local LLM support
- LangChain for agent orchestration
- Pydantic for data validation

---

**Need Help?** Check `AGENT_QUICK_START.md` for step-by-step setup.
