# 🚀 API Integration Guide - Hospital Admissions Forecasting

## 📋 Table of Contents
1. [Required Input Features](#required-input-features)
2. [Input Format](#input-format)
3. [Output Format](#output-format)
4. [Quick Start Example](#quick-start-example)
5. [API Wrapper Example](#api-wrapper-example)
6. [Agent Integration](#agent-integration)

---

## 📥 Required Input Features

### **Raw Data Columns (Minimum Required)**

Your input DataFrame must contain these **base columns**:

```python
REQUIRED_COLUMNS = [
    # Core temporal
    "date",                    # Date string or datetime (YYYY-MM-DD)
    
    # Historical admissions (for lag features)
    "admissions",              # Current/previous day's admissions
    # Note: lag_1, lag_7, and rolling_14 will be AUTO-CREATED from this column
    # If 'admissions' is missing, defaults (150) will be used (accuracy may be reduced)
    
    # Environmental
    "aqi",                     # Air Quality Index (0-500+)
    "temp",                    # Temperature (°C)
    "humidity",                # Humidity percentage (0-100)
    "rainfall",                # Rainfall in mm
    "wind_speed",              # Wind speed (km/h)
    
    # Social/Mobility
    "mobility_index",          # Mobility index (0-100, higher = more movement)
    "outbreak_index",          # Outbreak severity index (0-100)
    
    # Calendar
    "festival_flag",           # 1 if festival day, 0 otherwise
    "holiday_flag",            # 1 if holiday, 0 otherwise
    "weekday",                 # Day of week (0=Monday, 6=Sunday)
    "is_weekend",              # 1 if weekend, 0 otherwise
    
    # Hospital metadata
    "population_density",      # Population density (people/km²)
    "hospital_beds",           # Number of hospital beds
    "staff_count",             # Number of staff members
    "city_id",                 # City identifier (integer)
    "hospital_id_enc",         # Hospital identifier (integer)
]
```

### **Auto-Generated Features (41 Total)**

The pipeline automatically creates these from your raw data:

**Temporal Features (8):**
- `month`, `week_of_year`, `quarter`, `season`
- `day_sin`, `day_cos`, `month_sin`, `month_cos`

**AQI Interaction Features (4):**
- `aqi_above_150`, `aqi_above_200`, `aqi_above_300`, `aqi_severity`

**Engineered Interaction Features (10):**
- `temp_humidity`, `rainfall_injury_risk`, `aqi_respiratory_ratio`
- `aqi_temp`, `mobility_outbreak`, `temp_rainfall`, `aqi_mobility`
- `lag1_aqi`, `lag7_outbreak`, `rolling_aqi`

**Lag Features (3):**
- `lag_1_admissions`, `lag_7_admissions`, `rolling_14_admissions`

---

## 📊 Input Format

### **Single Prediction (One Row)**

```python
import pandas as pd
from datetime import datetime

# Example: Predict for tomorrow
input_data = pd.DataFrame({
    "date": ["2025-11-29"],
    "admissions": [150],  # Yesterday's admissions (for lag_1)
    "aqi": [180],
    "temp": [28.5],
    "humidity": [65],
    "rainfall": [12.3],
    "wind_speed": [15.2],
    "mobility_index": [75],
    "outbreak_index": [30],
    "festival_flag": [0],
    "holiday_flag": [0],
    "weekday": [4],  # Friday
    "is_weekend": [0],
    "population_density": [12000],
    "hospital_beds": [500],
    "staff_count": [200],
    "city_id": [1],  # Mumbai
    "hospital_id_enc": [101],
})
```

### **Batch Prediction (Multiple Rows)**

```python
# Example: Predict for next 7 days
input_data = pd.DataFrame({
    "date": ["2025-11-29", "2025-11-30", "2025-12-01", ...],
    "admissions": [150, 155, 148, ...],  # Historical admissions
    "aqi": [180, 195, 170, ...],
    "temp": [28.5, 29.0, 27.8, ...],
    # ... (all other columns)
})
```

---

## 📤 Output Format

### **Prediction Response**

The model returns a DataFrame with:

```python
{
    "date": ["2025-11-29", "2025-11-30", ...],
    "lower": [145.2, 148.5, ...],      # q10 quantile (10th percentile)
    "median": [162.8, 167.3, ...],     # q50 quantile (median prediction)
    "upper": [180.5, 186.2, ...],     # q90 quantile (90th percentile)
}
```

### **Interpretation**

- **`lower`**: 10% chance actual admissions will be below this value
- **`median`**: Most likely prediction (50th percentile)
- **`upper`**: 10% chance actual admissions will be above this value
- **Uncertainty Band**: Range between `lower` and `upper` (80% confidence interval)

---

## 🚀 Quick Start Example

### **Basic Usage**

```python
import pandas as pd
from src.pipeline.predict_pipeline import predict_df

# Prepare your input data
input_df = pd.DataFrame({
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
    "hospital_id_enc": [101],
})

# Make prediction (XGBoost only)
predictions = predict_df(input_df, mode="xgb")

# Or use ensemble (XGBoost + TFT)
predictions = predict_df(input_df, mode="ensemble", weight_tft=0.6)

print(predictions)
# Output:
#         date     lower    median     upper
# 0  2025-11-29  145.23   162.85   180.47
```

---

## 🔌 API Wrapper Example

### **Flask API**

```python
from flask import Flask, request, jsonify
import pandas as pd
from src.pipeline.predict_pipeline import predict_df
from src.pipeline.ensemble_predictor import predict_ensemble

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    """
    POST /predict
    Body: JSON array of input records
    """
    try:
        # Parse input
        data = request.json
        
        # Convert to DataFrame
        input_df = pd.DataFrame(data)
        
        # Validate required columns
        required = ["date", "admissions", "aqi", "temp", "humidity", 
                   "rainfall", "wind_speed", "mobility_index", "outbreak_index",
                   "festival_flag", "holiday_flag", "weekday", "is_weekend",
                   "population_density", "hospital_beds", "staff_count",
                   "city_id", "hospital_id_enc"]
        
        missing = [col for col in required if col not in input_df.columns]
        if missing:
            return jsonify({"error": f"Missing columns: {missing}"}), 400
        
        # Get mode from query params (default: ensemble)
        mode = request.args.get("mode", "ensemble")
        weight_tft = float(request.args.get("weight_tft", 0.6))
        
        # Make prediction
        if mode == "ensemble":
            predictions = predict_ensemble(input_df, weight_tft=weight_tft)
        else:
            predictions = predict_df(input_df, mode=mode)
        
        # Convert to JSON
        result = predictions.to_dict(orient="records")
        
        return jsonify({
            "status": "success",
            "predictions": result,
            "count": len(result)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

### **FastAPI Example**

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
import pandas as pd
from src.pipeline.predict_pipeline import predict_df

app = FastAPI(title="Hospital Admissions Forecast API")

class PredictionInput(BaseModel):
    date: str
    admissions: float
    aqi: float
    temp: float
    humidity: float
    rainfall: float
    wind_speed: float
    mobility_index: float
    outbreak_index: float
    festival_flag: int = Field(ge=0, le=1)
    holiday_flag: int = Field(ge=0, le=1)
    weekday: int = Field(ge=0, le=6)
    is_weekend: int = Field(ge=0, le=1)
    population_density: float
    hospital_beds: int
    staff_count: int
    city_id: int
    hospital_id_enc: int

class PredictionOutput(BaseModel):
    date: str
    lower: float
    median: float
    upper: float

@app.post("/predict", response_model=List[PredictionOutput])
async def predict(inputs: List[PredictionInput], mode: str = "ensemble"):
    """
    Predict hospital admissions for given input data.
    
    - **mode**: "xgb", "tft", or "ensemble" (default: ensemble)
    """
    try:
        # Convert to DataFrame
        input_df = pd.DataFrame([item.dict() for item in inputs])
        
        # Make prediction
        predictions = predict_df(input_df, mode=mode)
        
        # Convert to response format
        return predictions.to_dict(orient="records")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

---

## 🤖 Agent Integration

### **LangChain Agent Example**

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import pandas as pd
from src.pipeline.predict_pipeline import predict_df

class PredictAdmissionsInput(BaseModel):
    date: str = Field(description="Date for prediction (YYYY-MM-DD)")
    aqi: float = Field(description="Air Quality Index")
    temp: float = Field(description="Temperature in Celsius")
    humidity: float = Field(description="Humidity percentage")
    rainfall: float = Field(description="Rainfall in mm")
    mobility_index: float = Field(description="Mobility index (0-100)")
    outbreak_index: float = Field(description="Outbreak index (0-100)")
    # ... other fields

class PredictAdmissionsTool(BaseTool):
    name = "predict_hospital_admissions"
    description = """
    Predicts hospital patient admissions for a given date.
    Returns median prediction with lower and upper bounds (80% confidence interval).
    """
    args_schema = PredictAdmissionsInput
    
    def _run(self, **kwargs) -> str:
        # Prepare input DataFrame
        input_df = pd.DataFrame([kwargs])
        
        # Add default values for missing fields
        defaults = {
            "admissions": 150,  # Use average if not provided
            "wind_speed": 10.0,
            "festival_flag": 0,
            "holiday_flag": 0,
            "weekday": pd.to_datetime(kwargs["date"]).weekday(),
            "is_weekend": 1 if pd.to_datetime(kwargs["date"]).weekday() >= 5 else 0,
            "population_density": 10000,
            "hospital_beds": 500,
            "staff_count": 200,
            "city_id": 1,
            "hospital_id_enc": 101,
        }
        
        for key, value in defaults.items():
            if key not in kwargs:
                kwargs[key] = value
        
        input_df = pd.DataFrame([kwargs])
        
        # Make prediction
        predictions = predict_df(input_df, mode="ensemble")
        
        result = predictions.iloc[0]
        return f"""
        Prediction for {result['date']}:
        - Median: {result['median']:.1f} admissions
        - Lower bound (10th percentile): {result['lower']:.1f}
        - Upper bound (90th percentile): {result['upper']:.1f}
        - Uncertainty range: {result['upper'] - result['lower']:.1f} admissions
        """
    
    async def _arun(self, **kwargs) -> str:
        return self._run(**kwargs)

# Use in LangChain agent
from langchain.agents import initialize_agent, AgentType

tools = [PredictAdmissionsTool()]
agent = initialize_agent(
    tools,
    llm,  # Your LLM instance
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Example query
response = agent.run(
    "What will be the hospital admissions for Mumbai on 2025-12-01 "
    "if AQI is 200, temperature is 30°C, and there's an outbreak index of 50?"
)
```

---

## 📝 Notes

### **Important Considerations**

1. **Lag Features**: These are **automatically created** from the `admissions` column:
   - `lag_1_admissions`: Created from `admissions.shift(1)`
   - `lag_7_admissions`: Created from `admissions.shift(7)`
   - `rolling_14_admissions`: Created from `admissions.rolling(14).mean()`
   - **Note**: For best accuracy, provide historical admissions data. If missing, defaults (150) are used.

2. **Date Format**: Always provide `date` column as string (YYYY-MM-DD) or datetime

3. **Missing Values**: The pipeline will fill missing engineered features with 0, but base features should be provided

4. **Model Files**: Ensure these files exist in `models/`:
   - `global_q10.json`, `global_q50.json`, `global_q90.json`
   - `global_q50_spike.json`, `global_q50_extreme_spike.json`
   - `tft_global_q50.pth` (for ensemble mode)

5. **Prediction Modes**:
   - `mode="xgb"`: XGBoost only (faster, good for baseline)
   - `mode="tft"`: TFT median + XGB quantiles (experimental)
   - `mode="ensemble"`: Weighted blend of XGB + TFT (recommended, default)

---

## 🔗 Example cURL Request

```bash
curl -X POST http://localhost:5000/predict?mode=ensemble \
  -H "Content-Type: application/json" \
  -d '[
    {
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
    }
  ]'
```

---

## ✅ Quick Checklist

Before deploying:
- [ ] All model files exist in `models/` directory
- [ ] Input data has all required columns
- [ ] Date column is properly formatted
- [ ] Historical admissions data available (for lag features)
- [ ] API endpoint tested with sample data
- [ ] Error handling implemented
- [ ] Logging configured

---

**Need Help?** Check the logs for detailed error messages or feature requirements.

