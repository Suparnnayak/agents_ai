# 🏥 Hospital Admissions Forecasting & Autonomous Agent System

Production-grade time-series forecasting system with autonomous planning agents for hospital resource management.

---

## 📊 Overview

This system combines:
- **ML Forecasting**: Predicts daily hospital admissions using XGBoost, LightGBM, and TFT ensemble models
- **Autonomous Agents**: 4 specialized agents that generate operational plans (staffing, supplies, advisories)

### ML Model Performance
- **Overall Accuracy**: 91.76%
- **MAE**: 16.21 admissions
- **RMSE**: 23.28 admissions
- **R²**: 0.45
- **Quantile Coverage**: q10 (12%), q50 (52%), q90 (92%)

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone <repository-url>
cd "Lets go mumbai"

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Verify Models

Ensure model files exist in `models/`:
- `global_q10.json` - XGBoost 10th percentile model
- `global_q50.json` - XGBoost 50th percentile (median) model
- `global_q90.json` - XGBoost 90th percentile model
- `global_q50_spike.json` - First-stage spike booster
- `global_q50_extreme_spike.json` - Second-stage extreme spike booster
- `tft_global_q50.pth` - TFT model (optional, for ensemble mode)

### 3. Test ML Prediction

```bash
python example_prediction.py
```

### 4. Start ML API Server

```bash
python api_server.py
```

Test:
```bash
curl http://localhost:5000/health
```

### 5. Setup Agents (Optional)

**For Local Development (Ollama):**
```bash
# Install Ollama from https://ollama.com
ollama pull phi3
# Or
ollama pull llama3
```

**For Cloud LLM (Recommended for Production):**
Set environment variable:
```bash
# Google Gemini (Free tier available)
GOOGLE_API_KEY=your-api-key

# Or OpenAI
OPENAI_API_KEY=sk-...

# Or Hugging Face (Free)
HUGGINGFACE_API_KEY=hf_...
```

### 6. Start Agent API Server

```bash
python agent_api_server.py
```

Test:
```bash
curl http://localhost:5001/agents/health
```

---

## 📖 ML Model Usage

### Python API

```python
from src.pipeline.ensemble_predictor import predict_ensemble
import pandas as pd

# Prepare input data
df = pd.DataFrame({
    "date": ["2025-11-29"],
    "admissions": [150],
    "aqi": [180],
    "temp": [28.5],
    "humidity": [65],
    "rainfall": [12.3],
    "wind_speed": [15.2],
    "mobility_index": [75],
    "outbreak_index": [30],
    "festival_flag": [0],
    "holiday_flag": [0],
    "weekday": [4],
    "is_weekend": [0],
    "population_density": [12000],
    "hospital_beds": [500],
    "staff_count": [200],
    "city_id": [1],
    "hospital_id_enc": [101]
})

# Make prediction
predictions = predict_ensemble(df)
print(predictions)
# Output:
#    date      lower    median     upper
# 0  2025-11-29  145.2   162.8    180.5
```

### REST API

**Health Check:**
```bash
curl http://localhost:5000/health
```

**Single Prediction:**
```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "data": [{
      "date": "2025-11-29",
      "admissions": 150,
      "aqi": 180,
      "temp": 28.5,
      "humidity": 65,
      "rainfall": 12.3,
      "wind_speed": 15.2,
      "mobility_index": 75,
      "outbreak_index": 30,
      "festival_flag": 0,
      "holiday_flag": 0,
      "weekday": 4,
      "is_weekend": 0,
      "population_density": 12000,
      "hospital_beds": 500,
      "staff_count": 200,
      "city_id": 1,
      "hospital_id_enc": 101
    }],
    "mode": "ensemble"
  }'
```

**Response:**
```json
{
  "status": "success",
  "predictions": [
    {
      "date": "2025-11-29",
      "lower": 145.2,
      "median": 162.8,
      "upper": 180.5
    }
  ],
  "count": 1,
  "mode": "ensemble"
}
```

---

## 🤖 Agent System Usage

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
```

### REST API

**Complete Pipeline:**
```bash
curl -X POST http://localhost:5001/agents/run \
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

**Individual Agents:**
```bash
# Monitor only
curl -X POST http://localhost:5001/agents/monitor \
  -H "Content-Type: application/json" \
  -d '{
    "aqi": 240,
    "festival_score": 1.0,
    "weather_risk": 0.3,
    "disease_sensitivity": 0.5
  }'
```

**Agent Output Format:**
```json
{
  "requestId": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-05T10:30:00Z",
  "hospitalId": "HOSP-123",
  "predictedInflow": 250.5,
  "monitorReport": {
    "alertLevel": "high",
    "riskFactors": ["AQI > 200", "Festival season"],
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
    "commonMedicines": ["Paracetamol", "Ibuprofen"],
    "specialMedicines": ["Ventilator medications"]
  },
  "advisory": {
    "publicAdvisory": "High pollution levels detected...",
    "triageRules": "Prioritize respiratory cases...",
    "teleconsultation": "Increase teleconsultation capacity...",
    "pollutionCare": "Ensure adequate nebulizer availability..."
  },
  "recommendedActions": [
    "Notify respiratory teams about alert level high",
    "Stage 85 oxygen cylinders near ER"
  ]
}
```

---

## 🏗️ Architecture

### ML Model Architecture

**Ensemble Model:**
```
Final Median = 0.6 × XGBoost_q50 + 0.4 × TFT_q50
Final Lower  = XGBoost_q10 (with spike adjustments)
Final Upper  = XGBoost_q90 (with spike adjustments)
```

**Spike Correction System:**
1. **General Spike Booster**: Targets samples above 70th percentile
2. **Extreme Spike Booster**: Targets top 1% of positive residuals

**Feature Engineering:**
- 41 features including temporal, lag, AQI interactions, weather, social, and hospital metadata
- Lag features (`lag_1_admissions`, `lag_7_admissions`, `rolling_14_admissions`) are auto-created from `admissions` column

### Agent Architecture

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

**4 Specialized Agents:**
1. **Monitor Agent** - Evaluates environmental and seasonal risks (AQI, weather, festivals)
2. **Staffing Planner** - Plans doctor, nurse, and support staff requirements
3. **Supplies Planner** - Plans medical supplies (oxygen, beds, medicines)
4. **Advisory Agent** - Generates public advisories, triage rules, and clinical guidance
5. **Coordinator** - Aggregates all outputs into a final operational plan

---

## 📋 Required Input Features

### ML Model Input (18 base fields)

```json
{
  "date": "YYYY-MM-DD",
  "admissions": 150,
  "aqi": 180,
  "temp": 28.5,
  "humidity": 65,
  "rainfall": 12.3,
  "wind_speed": 15.2,
  "mobility_index": 75,
  "outbreak_index": 30,
  "festival_flag": 0,
  "holiday_flag": 0,
  "weekday": 4,
  "is_weekend": 0,
  "population_density": 12000,
  "hospital_beds": 500,
  "staff_count": 200,
  "city_id": 1,
  "hospital_id_enc": 101
}
```

**Note:** Lag features (`lag_1_admissions`, `lag_7_admissions`, `rolling_14_admissions`) are automatically created from the `admissions` field if missing.

---

## 🔧 Configuration

### ML Model Configuration

Set environment variables (optional):
```bash
PREDICTION_MODE=ensemble    # "xgb", "tft", or "ensemble"
TFT_WEIGHT=0.6              # TFT weight in ensemble (0-1)
PORT=5000                   # API server port
HOST=0.0.0.0                # API server host
```

### Agent Configuration

**Environment Variables:**
```bash
# Prediction API
AGENT_PREDICTION_API_URL=https://ai-health-agent-vuol.onrender.com/predict

# LLM Configuration (choose one)
GOOGLE_API_KEY=your-api-key          # Google Gemini (free tier)
OPENAI_API_KEY=sk-...                 # OpenAI
HUGGINGFACE_API_KEY=hf_...            # Hugging Face (free)
TOGETHER_API_KEY=...                   # Together.ai

# Ollama (for local development)
AGENT_OLLAMA_BASE_URL=http://localhost:11434
AGENT_OLLAMA_MODEL=phi3  # Options: phi3, llama3, mistral
AGENT_TEMPERATURE=0.1    # Lower = more deterministic
```

**LLM Provider Priority:**
1. Google Gemini (if `GOOGLE_API_KEY` is set)
2. OpenAI (if `OPENAI_API_KEY` is set)
3. Hugging Face (if `HUGGINGFACE_API_KEY` is set)
4. Together.ai (if `TOGETHER_API_KEY` is set)
5. Ollama (fallback, requires local installation)

---

## 🌐 Deployment

### ML Model API (Render)

1. **Create `render.yaml`:**
```yaml
services:
  - type: web
    name: hospital-forecast-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn api_server:app --bind 0.0.0.0:$PORT --workers 2
    envVars:
      - key: PREDICTION_MODE
        value: ensemble
    healthCheckPath: /health
    plan: starter
```

2. **Deploy:**
   - Push to GitHub
   - Connect repo to Render
   - Auto-deploy

### Agent API (Render)

1. **Create `render_agents.yaml`:**
```yaml
services:
  - type: web
    name: hospital-agent-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn agent_api_server:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
    envVars:
      - key: AGENT_PREDICTION_API_URL
        value: https://your-ml-api.onrender.com/predict
      - key: GOOGLE_API_KEY
        value: your-api-key
    healthCheckPath: /agents/health
    plan: starter
```

2. **Set Environment Variables in Render Dashboard:**
   - `GOOGLE_API_KEY` (or other LLM API key)
   - `AGENT_PREDICTION_API_URL`

3. **Deploy:**
   - Push to GitHub
   - Connect repo to Render
   - Auto-deploy

### Keep Services Alive (Free Tier)

**Option 1: UptimeRobot (Free)**
1. Sign up at https://uptimerobot.com
2. Add monitor for your API URL
3. Set interval to 5 minutes
4. Service stays awake

**Option 2: Self-Hosted Script**
```bash
python keep_alive.py
```

---

## ⚙️ Full Automation (Zero Manual Intervention)

### Quick Setup - GitHub Actions (Recommended)

**Fully automated pipeline - runs daily, saves results, sends notifications!**

1. **Add Secrets to GitHub:**
   - Go to: Repository → Settings → Secrets and variables → Actions
   - Add these secrets:
     - `AGENT_API_URL` = `https://agents-ai-hfpb.onrender.com/agents/run`
     - `ML_API_URL` = `https://ai-health-agent-vuol.onrender.com/predict`
     - `HOSPITAL_ID` = `HOSP-123`
     - `DISEASE_SENSITIVITY` = `0.5`
     - `DATA_SOURCE` = `sample` (or `api`/`file`)

2. **Push Code:**
   ```bash
   git add .
   git commit -m "Setup automation"
   git push
   ```

3. **Done!** ✅
   - Runs automatically daily at 8 AM UTC
   - Saves results to `plans/` directory
   - Uploads as GitHub artifacts
   - Commits results to repo

**Manual Trigger:** Go to Actions tab → "Run Agents Daily" → "Run workflow"

### Other Automation Options

- **Render Cron Jobs** - Free tier available
- **Local Cron** - Linux/Mac: `crontab -e`
- **Windows Task Scheduler** - Built-in scheduler
- **Cloud Schedulers** - AWS, GCP, Azure

**See `AUTOMATION_GUIDE.md` for complete setup instructions!**

### Run Manually

```bash
# Using the fully automated script
python auto_run_agents.py

# Or using the simple script
python automate_agents.py
```

---

## 🧪 Training Models

### Train Global Models

```bash
python -m src.pipeline.train_pipeline
```

Or use the training script:
```python
from src.pipeline.train_pipeline import run_training_global

results = run_training_global(
    output_dir="models",
    use_optuna=False,  # Set True for hyperparameter tuning
    optuna_trials=30
)
```

### Train TFT Model (Optional)

```python
from src.pipeline.tft_training_pipeline import run_tft_training

run_tft_training()
```

### Training Parameters

- **XGBoost**: Quantile regression with `reg:absoluteerror` objective
- **TFT**: `input_dim=41`, `hidden_size=128`, `dropout=0.1`, `epochs=30`, `lr=1e-3`
- **Spike Boosters**: Aggressive parameters for extreme event detection

---

## 📁 Project Structure

```
.
├── src/
│   ├── pipeline/
│   │   ├── train_pipeline.py          # Training orchestration
│   │   ├── ensemble_predictor.py      # Ensemble prediction
│   │   ├── predict_pipeline.py       # Prediction pipeline
│   │   ├── feature_engineering.py     # Feature engineering
│   │   ├── feature_engineering_unified.py  # Unified 41 features
│   │   └── utils.py                   # Model save/load utilities
│   ├── components/
│   │   └── model_trainer.py           # Model training logic
│   └── models/
│       ├── ensemble.py
│       └── tft_model.py
├── agents/
│   ├── config.py                    # Configuration management
│   ├── schemas.py                   # Pydantic data models
│   ├── llm_client.py                # LLM integration
│   ├── prediction_client.py         # ML API client
│   ├── monitor_agent.py             # Monitor agent
│   ├── planning_agent.py            # Staffing & Supplies planners
│   ├── advisory_agent.py            # Advisory agent
│   ├── coordinator_agent.py        # Plan coordinator
│   └── run_pipeline.py              # CLI entrypoint
├── models/                          # Saved model files
│   ├── global_q10.json
│   ├── global_q50.json
│   ├── global_q90.json
│   ├── global_q50_spike.json
│   ├── global_q50_extreme_spike.json
│   └── tft_global_q50.pth
├── api_server.py                    # ML Flask API server
├── agent_api_server.py              # Agent Flask API server
├── example_prediction.py            # ML usage examples
├── automate_agents.py              # Automation script
├── samples/
│   └── sample_request.json          # Example input
├── requirements.txt                # Dependencies
├── render.yaml                     # ML API deployment config
├── render_agents.yaml              # Agent API deployment config
└── Procfile                        # Production server config
```

---

## 🐛 Troubleshooting

### ML Model Issues

**Model Not Found:**
```
FileNotFoundError: Model not found at models/global_q50.json
```
**Solution:** Train models first using `run_training_global()`

**TFT Model Loading Error:**
```
RuntimeError: Error(s) in loading state_dict
```
**Solution:** Ensemble will fall back to XGBoost-only mode automatically

**Missing Features:**
```
ValueError: Missing required features: ['lag_1_admissions']
```
**Solution:** Lag features are auto-created from `admissions` column

### Agent Issues

**LLM Connection Failed:**
```
Error: Connection refused to http://localhost:11434
```
**Solution:**
- Start Ollama: `ollama serve`
- Or use cloud LLM (set `GOOGLE_API_KEY`, `OPENAI_API_KEY`, etc.)

**Gemini Model Error:**
```
404 models/gemini-1.5-flash is not found
```
**Solution:** Already fixed - using `gemini-pro` model. Push code to deploy.

**Prediction API Timeout:**
```
ReadTimeout: The read operation timed out
```
**Solution:**
- Prediction API may be sleeping (Render free tier)
- Use UptimeRobot to keep it alive
- Or upgrade to paid tier

**LLM Output Parsing Error:**
```
OutputParserException: Failed to parse JSON
```
**Solution:**
- JSON repair logic is already implemented
- Try a different model (e.g., `llama3` instead of `phi3`)
- Lower temperature: `AGENT_TEMPERATURE=0.1`

### API Timeout (Render Free Tier)

**Solution:**
- Use UptimeRobot to keep service alive (free tier)
- Upgrade to paid tier (no spin-downs)
- Increase timeout in client

---

## 🔄 Model Updates

To retrain models with new data:

1. **Update training data** in `generated_datasets_ml_ready/`
2. **Run training:**
   ```python
   from src.pipeline.train_pipeline import run_training_global
   run_training_global(output_dir="models")
   ```
3. **Deploy updated models** to your API server

---

## 📈 Performance Monitoring

**ML Model:**
- **Quantile Coverage**: Should be ~10% (q10), ~50% (q50), ~90% (q90)
- **MAE/RMSE**: Track over time
- **Spike Detection**: Monitor extreme event predictions

**Agents:**
- Monitor API response times
- Track LLM token usage
- Log agent execution traces

---

## 💡 Best Practices

1. **Use Cloud LLM** for production (Gemini free tier, Together.ai is very cheap)
2. **Monitor API health** with UptimeRobot
3. **Save plans** to database for tracking
4. **Set up alerts** for high alert levels
5. **Automate daily runs** with GitHub Actions or cron
6. **Use Gunicorn** for production Flask servers
7. **Set proper timeouts** for API calls

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

---

## 📄 License

[Your License Here]

---

## 🙏 Acknowledgments

- XGBoost team for quantile regression
- PyTorch team for TFT implementation
- LangChain for agent orchestration
- Pydantic for data validation
- Render/Railway for hosting infrastructure
- Ollama for local LLM support

---

**Built with ❤️ for healthcare forecasting**
