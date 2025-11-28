# 🏥 Hospital Admissions Forecasting System

Production-grade time-series forecasting system for hospital patient inflow prediction using XGBoost, LightGBM, and Temporal Fusion Transformer (TFT).

## 🎯 Features

- **Multi-Model Ensemble**: Combines XGBoost quantile models with TFT for robust predictions
- **Spike Detection**: Two-stage spike correction system for extreme events
- **Quantile Forecasting**: Provides lower (q10), median (q50), and upper (q90) bounds
- **41 Engineered Features**: Temporal, AQI interactions, and domain-specific features
- **Production-Ready API**: Flask-based REST API for easy integration

## 📊 Model Performance

- **Overall Accuracy**: 91.76%
- **MAE**: 16.21 admissions
- **RMSE**: 23.28 admissions
- **R²**: 0.45

## 🚀 Quick Start

### **1. Installation**

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

### **2. Verify Models**

Ensure model files exist in `models/`:
- `global_q10.json`, `global_q50.json`, `global_q90.json`
- `global_q50_spike.json`, `global_q50_extreme_spike.json`
- `tft_global_q50.pth` (optional, for ensemble mode)

### **3. Run Example**

```bash
python example_prediction.py
```

### **4. Start API Server**

```bash
python api_server.py
```

Test the API:
```bash
curl http://localhost:5000/health
```

## 📖 Usage

### **Python API**

```python
from src.pipeline.ensemble_predictor import predict_ensemble
import pandas as pd

# Prepare input data
df = pd.DataFrame({
    "date": ["2025-11-29"],
    "admissions": [150],
    "aqi": [180],
    "temp": [28.5],
    # ... (see API_INTEGRATION_GUIDE.md for full list)
})

# Make prediction
predictions = predict_ensemble(df)
print(predictions)
```

### **REST API**

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

## 📁 Project Structure

```
.
├── src/
│   ├── components/          # Data ingestion, transformation, model training
│   ├── pipeline/            # Training and prediction pipelines
│   ├── models/              # TFT model and ensemble logic
│   └── utils/               # Utilities and evaluation
├── models/                  # Trained model files
├── generated_datasets_ml_ready/  # Training data
├── api_server.py           # Production API server
├── example_prediction.py   # Usage examples
├── requirements.txt        # Python dependencies
└── API_INTEGRATION_GUIDE.md  # Detailed integration guide
```

## 📋 Required Input Features

Your input DataFrame must contain these **18 base columns**:

1. `date` - Date (YYYY-MM-DD)
2. `admissions` - Previous day's admissions (lag features auto-created)
3. `aqi` - Air Quality Index
4. `temp` - Temperature (°C)
5. `humidity` - Humidity (%)
6. `rainfall` - Rainfall (mm)
7. `wind_speed` - Wind speed (km/h)
8. `mobility_index` - Mobility index (0-100)
9. `outbreak_index` - Outbreak severity (0-100)
10. `festival_flag` - 1 if festival, 0 otherwise
11. `holiday_flag` - 1 if holiday, 0 otherwise
12. `weekday` - Day of week (0=Mon, 6=Sun)
13. `is_weekend` - 1 if weekend, 0 otherwise
14. `population_density` - People/km²
15. `hospital_beds` - Number of beds
16. `staff_count` - Number of staff
17. `city_id` - City identifier
18. `hospital_id_enc` - Hospital identifier

**Note**: The pipeline automatically creates 41 engineered features from these inputs.

## 📤 Output Format

```python
{
    "date": "2025-11-29",
    "lower": 145.2,    # 10th percentile (lower bound)
    "median": 162.8,   # 50th percentile (most likely)
    "upper": 180.5     # 90th percentile (upper bound)
}
```

## 🔧 Configuration

Set environment variables (optional):

```bash
PREDICTION_MODE=ensemble    # "xgb", "tft", or "ensemble"
TFT_WEIGHT=0.6              # TFT weight in ensemble (0-1)
PORT=5000                   # API server port
HOST=0.0.0.0                # API server host
```

## 📚 Documentation

- **[API_INTEGRATION_GUIDE.md](API_INTEGRATION_GUIDE.md)** - Complete API integration guide
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Production deployment instructions
- **[example_prediction.py](example_prediction.py)** - Working code examples

## 🧪 Training Models

To retrain models:

```bash
# Train global XGBoost models
python -c "from src.pipeline.train_pipeline import run_training_global; run_training_global()"

# Train TFT model (optional)
python -c "from src.pipeline.tft_training_pipeline import run_tft_training; run_tft_training()"
```

## 🚀 Deployment

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for:
- Docker deployment
- Cloud deployment (AWS, GCP, Azure)
- Production best practices
- Security considerations

## 📝 License

[Your License Here]

## 🤝 Contributing

[Contributing Guidelines]

## 📞 Support

For issues or questions, please check:
1. [API_INTEGRATION_GUIDE.md](API_INTEGRATION_GUIDE.md)
2. [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
3. Example code in `example_prediction.py`

---

**Built with ❤️ for healthcare forecasting**

