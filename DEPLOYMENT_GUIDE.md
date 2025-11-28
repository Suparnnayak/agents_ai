# 🚀 Deployment Guide - Hospital Admissions Forecast API

## 📋 Pre-Deployment Checklist

### ✅ **1. Model Files Verification**

Ensure all model files exist in `models/` directory:

```bash
models/
├── global_q10.json              # XGBoost q10 quantile model
├── global_q50.json              # XGBoost q50 (median) model
├── global_q90.json              # XGBoost q90 quantile model
├── global_q50_spike.json        # Spike correction booster
├── global_q50_extreme_spike.json # Extreme spike booster
└── tft_global_q50.pth           # TFT model (optional, for ensemble)
```

**Verify:**
```bash
python -c "from src.pipeline.predict_pipeline import predict_df; import pandas as pd; df=pd.DataFrame({'date':['2025-11-29'],'admissions':[150],'aqi':[180],'temp':[28.5],'humidity':[65],'rainfall':[12.3],'wind_speed':[15.2],'mobility_index':[75],'outbreak_index':[30],'festival_flag':[0],'holiday_flag':[0],'weekday':[4],'is_weekend':[0],'population_density':[12000],'hospital_beds':[500],'staff_count':[200],'city_id':[1],'hospital_id_enc':[101]}); print(predict_df(df, mode='xgb'))"
```

### ✅ **2. Dependencies Installation**

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### ✅ **3. Environment Variables (Optional)**

Create `.env` file (optional):

```bash
# .env
PREDICTION_MODE=ensemble    # or "xgb" for faster predictions
TFT_WEIGHT=0.6              # TFT weight in ensemble (0-1)
PORT=5000                   # API server port
HOST=0.0.0.0                # API server host
```

---

## 🚀 **Deployment Options**

### **Option 1: Simple Flask Server (Development/Testing)**

```bash
# Run directly
python api_server.py

# Or with custom port
PORT=8080 python api_server.py
```

**Test:**
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

### **Option 2: Production with Gunicorn (Linux/Mac)**

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 api_server:app

# With logging
gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile - --error-logfile - api_server:app
```

### **Option 3: Docker Deployment**

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY models/ ./models/
COPY api_server.py .

# Expose port
EXPOSE 5000

# Run server
CMD ["python", "api_server.py"]
```

**Build and run:**
```bash
docker build -t hospital-forecast-api .
docker run -p 5000:5000 hospital-forecast-api
```

### **Option 4: Cloud Deployment**

#### **AWS Lambda (Serverless)**

Use `serverless` framework or AWS SAM:

```yaml
# serverless.yml
service: hospital-forecast

provider:
  name: aws
  runtime: python3.10
  memorySize: 1024
  timeout: 30

functions:
  predict:
    handler: api_server.lambda_handler
    events:
      - http:
          path: predict
          method: post
```

#### **Google Cloud Run**

```bash
# Build container
gcloud builds submit --tag gcr.io/PROJECT_ID/hospital-forecast

# Deploy
gcloud run deploy hospital-forecast \
  --image gcr.io/PROJECT_ID/hospital-forecast \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### **Azure App Service**

```bash
# Create app service
az webapp create --resource-group myResourceGroup \
  --plan myAppServicePlan --name hospital-forecast-api \
  --runtime "PYTHON|3.10"

# Deploy
az webapp deployment source config-zip \
  --resource-group myResourceGroup \
  --name hospital-forecast-api \
  --src app.zip
```

---

## 🔒 **Security Considerations**

### **1. API Authentication**

Add authentication middleware:

```python
# api_server.py
from functools import wraps
import os

API_KEY = os.getenv("API_KEY", "")

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if API_KEY and api_key != API_KEY:
            return jsonify({"error": "Invalid API key"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route("/predict", methods=["POST"])
@require_api_key
def predict():
    # ... existing code
```

### **2. Rate Limiting**

```bash
pip install flask-limiter
```

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@app.route("/predict", methods=["POST"])
@limiter.limit("10 per minute")
def predict():
    # ... existing code
```

### **3. Input Validation**

Already implemented in `api_server.py` - validates required columns and data types.

---

## 📊 **Monitoring & Logging**

### **1. Application Logs**

Logs are automatically written via `src.pipeline.logger`. Configure log level:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### **2. Health Check Endpoint**

```bash
curl http://localhost:5000/health
```

### **3. Metrics Collection**

Add Prometheus metrics (optional):

```bash
pip install prometheus-flask-exporter
```

```python
from prometheus_flask_exporter import PrometheusMetrics

metrics = PrometheusMetrics(app)
```

---

## 🧪 **Testing Before Deployment**

### **1. Unit Test**

```bash
python -m pytest tests/ -v
```

### **2. Integration Test**

```bash
# Test API endpoint
python -c "
import requests
import json

data = {
    'data': [{
        'date': '2025-11-29',
        'admissions': 150,
        'aqi': 180,
        'temp': 28.5,
        'humidity': 65,
        'rainfall': 12.3,
        'wind_speed': 15.2,
        'mobility_index': 75,
        'outbreak_index': 30,
        'festival_flag': 0,
        'holiday_flag': 0,
        'weekday': 4,
        'is_weekend': 0,
        'population_density': 12000,
        'hospital_beds': 500,
        'staff_count': 200,
        'city_id': 1,
        'hospital_id_enc': 101
    }]
}

response = requests.post('http://localhost:5000/predict', json=data)
print(response.json())
"
```

### **3. Load Testing**

```bash
pip install locust
```

Create `locustfile.py`:

```python
from locust import HttpUser, task

class ForecastUser(HttpUser):
    @task
    def predict(self):
        self.client.post("/predict", json={
            "data": [{
                "date": "2025-11-29",
                "admissions": 150,
                # ... other fields
            }]
        })
```

Run:
```bash
locust -f locustfile.py --host=http://localhost:5000
```

---

## 📝 **Deployment Checklist**

- [ ] All model files exist in `models/` directory
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] API server starts without errors
- [ ] Health check endpoint responds (`/health`)
- [ ] Test prediction works (`/predict`)
- [ ] Error handling tested (invalid input, missing columns)
- [ ] Logging configured
- [ ] Security measures implemented (API key, rate limiting)
- [ ] Monitoring set up (health checks, metrics)
- [ ] Documentation updated
- [ ] Environment variables configured
- [ ] Backup strategy for model files

---

## 🆘 **Troubleshooting**

### **Issue: Model files not found**

```bash
# Check model files
ls -la models/

# Verify paths in code
python -c "from pathlib import Path; print(Path('models').exists())"
```

### **Issue: Import errors**

```bash
# Verify Python path
python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### **Issue: Memory errors**

- Reduce batch size
- Use `mode="xgb"` instead of `mode="ensemble"` (no TFT model needed)
- Increase server memory allocation

### **Issue: Slow predictions**

- Use `mode="xgb"` for faster predictions
- Enable model caching (load models once at startup)
- Use GPU for TFT model (if available)

---

## 📞 **Support**

For issues or questions:
1. Check logs: `tail -f logs/app.log`
2. Test health endpoint: `curl http://localhost:5000/health`
3. Verify model files: `ls -la models/`
4. Check API documentation: `curl http://localhost:5000/`

---

**Ready to deploy!** 🚀

