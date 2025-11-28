# 🏥 Hospital Admissions Forecasting - ML Model System

Production-grade time-series forecasting system for hospital patient inflow prediction using XGBoost, LightGBM, and Temporal Fusion Transformer (TFT).

## 📊 Overview

This ML system predicts daily hospital admissions with:
- **Quantile Forecasting**: Lower (q10), median (q50), and upper (q90) bounds
- **Multi-Model Ensemble**: Combines XGBoost quantile models with TFT
- **Spike Detection**: Two-stage spike correction system for extreme events
- **41 Engineered Features**: Temporal, AQI interactions, and domain-specific features
- **Production-Ready API**: Flask-based REST API for easy integration

## 🎯 Model Performance

- **Overall Accuracy**: 91.76%
- **MAE**: 16.21 admissions
- **RMSE**: 23.28 admissions
- **R²**: 0.45
- **Quantile Coverage**: q10 (12%), q50 (52%), q90 (92%)

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

### 3. Run Example Prediction

```bash
python example_prediction.py
```

### 4. Start API Server

```bash
python api_server.py
```

Test the API:
```bash
curl http://localhost:5000/health
```

## 📖 Usage

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

#### Health Check
```bash
curl http://localhost:5000/health
```

#### Single Prediction
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

#### Response Format
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

## 🏗️ Model Architecture

### Ensemble Model

The system uses a weighted ensemble of XGBoost and TFT models:

```
Final Median = 0.6 × XGBoost_q50 + 0.4 × TFT_q50
Final Lower  = XGBoost_q10 (with spike adjustments)
Final Upper  = XGBoost_q90 (with spike adjustments)
```

### Spike Correction System

Two-stage spike correction to handle extreme events:

1. **General Spike Booster**: Targets samples above 70th percentile
   - Trained on residuals from base median model
   - Aggressive parameters for spike detection

2. **Extreme Spike Booster**: Targets top 1% of positive residuals
   - Second-stage correction for most extreme underpredictions
   - Even more aggressive scaling

### Feature Engineering

41 features including:
- **Temporal**: `weekday`, `is_weekend`, `month`, `day_of_year`
- **Lag Features**: `lag_1_admissions`, `lag_7_admissions`, `rolling_14_admissions`
- **AQI Interactions**: `aqi × temp`, `aqi × humidity`
- **Weather**: `temp`, `humidity`, `rainfall`, `wind_speed`
- **Social**: `mobility_index`, `outbreak_index`, `festival_flag`, `holiday_flag`
- **Hospital**: `hospital_beds`, `staff_count`, `population_density`

## 🔧 Training Models

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

### Train City-Specific Models

```python
from src.pipeline.train_pipeline import run_training_for_city

results = run_training_for_city(
    city="Mumbai",
    output_dir="models",
    use_optuna=False
)
```

### Training Parameters

- **XGBoost**: Quantile regression with `reg:absoluteerror` objective
- **TFT**: `input_dim=41`, `hidden_size=128`, `dropout=0.1`, `epochs=30`, `lr=1e-3`
- **Spike Boosters**: Aggressive parameters for extreme event detection

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
│   └── ...
├── models/                             # Saved model files
│   ├── global_q10.json
│   ├── global_q50.json
│   ├── global_q90.json
│   ├── global_q50_spike.json
│   ├── global_q50_extreme_spike.json
│   └── tft_global_q50.pth
├── api_server.py                      # Flask API server
├── example_prediction.py               # Example usage
└── requirements.txt                    # Dependencies
```

## 🌐 Deployment

### Render (Recommended)

1. **Create `render.yaml`:**
```yaml
services:
  - type: web
    name: hospital-forecast-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python api_server.py
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

### Railway

1. **Create `railway.json`:**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python api_server.py"
  }
}
```

2. **Deploy:**
   - Connect GitHub repo
   - Railway auto-detects and deploys

### Docker

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "api_server.py"]
```

```bash
docker build -t hospital-forecast-api .
docker run -p 5000:5000 hospital-forecast-api
```

## 📊 Input Requirements

### Required Fields (18 base fields)

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

## 🔍 API Modes

### Ensemble Mode (Default)
```json
{
  "mode": "ensemble",
  "weight_tft": 0.6
}
```
Combines XGBoost (60%) and TFT (40%) for median prediction.

### XGBoost Only
```json
{
  "mode": "xgb"
}
```
Uses only XGBoost quantile models (faster, no TFT dependency).

### TFT Only
```json
{
  "mode": "tft"
}
```
Uses only TFT model (requires PyTorch).

## 🧪 Testing

### Test Prediction Pipeline

```bash
python example_prediction.py
```

### Test API Locally

```bash
# Start server
python api_server.py

# Test health
curl http://localhost:5000/health

# Test prediction
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```

### Test Deployment

```bash
# Test deployed API
curl https://your-api.onrender.com/health
curl -X POST https://your-api.onrender.com/predict \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```

## 🐛 Troubleshooting

### Model Not Found
```
FileNotFoundError: Model not found at models/global_q50.json
```
**Solution:** Train models first using `run_training_global()`

### TFT Model Loading Error
```
RuntimeError: Error(s) in loading state_dict
```
**Solution:** Ensemble will fall back to XGBoost-only mode automatically

### Missing Features
```
ValueError: Missing required features: ['lag_1_admissions']
```
**Solution:** Lag features are auto-created from `admissions` column

### API Timeout
**Solution:** 
- Use UptimeRobot to keep service alive (free tier)
- Upgrade to paid tier (no spin-downs)
- Increase timeout in client

## 📚 Additional Documentation

- `API_INTEGRATION_GUIDE.md` - Detailed API integration guide
- `DEPLOYMENT_SOLUTIONS.md` - Deployment options and solutions
- `QUICK_FIX_RENDER.md` - Quick fixes for Render deployment

## 🔄 Model Updates

To retrain models with new data:

1. **Update training data** in `generated_datasets_ml_ready/`
2. **Run training:**
   ```python
   from src.pipeline.train_pipeline import run_training_global
   run_training_global(output_dir="models")
   ```
3. **Deploy updated models** to your API server

## 📈 Performance Monitoring

Monitor model performance:
- **Quantile Coverage**: Should be ~10% (q10), ~50% (q50), ~90% (q90)
- **MAE/RMSE**: Track over time
- **Spike Detection**: Monitor extreme event predictions

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

- XGBoost team for quantile regression
- PyTorch team for TFT implementation
- Render/Railway for hosting infrastructure

---

**Need Help?** Check `API_INTEGRATION_GUIDE.md` for detailed integration examples.

