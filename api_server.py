"""
Production API Server for Hospital Admissions Forecasting
Run with: python api_server.py
"""
from flask import Flask, request, jsonify
import pandas as pd
import traceback
from datetime import datetime
import os

from src.pipeline.predict_pipeline import predict_df
from src.pipeline.ensemble_predictor import predict_ensemble
from src.pipeline.logger import get_logger

app = Flask(__name__)
logger = get_logger(__name__)

# Configuration
DEFAULT_MODE = os.getenv("PREDICTION_MODE", "ensemble")
DEFAULT_WEIGHT_TFT = float(os.getenv("TFT_WEIGHT", "0.6"))
# Render automatically sets PORT environment variable
PORT = int(os.getenv("PORT", "5000"))
HOST = os.getenv("HOST", "0.0.0.0")


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "hospital-admissions-forecast",
        "timestamp": datetime.now().isoformat()
    })


@app.route("/predict", methods=["POST"])
def predict():
    """
    Predict hospital admissions.
    
    Request Body (JSON):
    {
        "data": [
            {
                "date": "2025-11-29",
                "admissions": 150,
                "aqi": 180,
                "temp": 28.5,
                ...
            }
        ],
        "mode": "ensemble",  # optional: "xgb", "tft", "ensemble"
        "weight_tft": 0.6    # optional: TFT weight for ensemble (0-1)
    }
    
    Response:
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
        "count": 1
    }
    """
    try:
        # Parse request
        data = request.json
        
        if not data or "data" not in data:
            return jsonify({"error": "Missing 'data' field in request body"}), 400
        
        input_data = data["data"]
        mode = data.get("mode", DEFAULT_MODE)
        weight_tft = float(data.get("weight_tft", DEFAULT_WEIGHT_TFT))
        
        # Validate mode
        if mode not in ["xgb", "tft", "ensemble"]:
            return jsonify({"error": f"Invalid mode: {mode}. Must be 'xgb', 'tft', or 'ensemble'"}), 400
        
        # Convert to DataFrame
        input_df = pd.DataFrame(input_data)
        
        # Validate required columns
        required = [
            "date", "admissions", "aqi", "temp", "humidity", "rainfall",
            "wind_speed", "mobility_index", "outbreak_index",
            "festival_flag", "holiday_flag", "weekday", "is_weekend",
            "population_density", "hospital_beds", "staff_count",
            "city_id", "hospital_id_enc"
        ]
        
        missing = [col for col in required if col not in input_df.columns]
        if missing:
            return jsonify({
                "error": f"Missing required columns: {missing}",
                "required": required
            }), 400
        
        # Make prediction
        logger.info(f"📊 Making prediction: mode={mode}, rows={len(input_df)}")
        
        if mode == "ensemble":
            predictions = predict_ensemble(input_df, weight_tft=weight_tft)
        else:
            predictions = predict_df(input_df, mode=mode, weight_tft=weight_tft)
        
        # Convert to JSON
        result = predictions.to_dict(orient="records")
        
        return jsonify({
            "status": "success",
            "predictions": result,
            "count": len(result),
            "mode": mode
        })
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Prediction error: {e}\n{traceback.format_exc()}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route("/predict/batch", methods=["POST"])
def predict_batch():
    """
    Batch prediction endpoint (alias for /predict).
    Accepts CSV file upload or JSON array.
    """
    return predict()


@app.route("/", methods=["GET"])
def index():
    """API documentation endpoint."""
    return jsonify({
        "service": "Hospital Admissions Forecast API",
        "version": "1.0.0",
        "endpoints": {
            "GET /health": "Health check",
            "POST /predict": "Make predictions (JSON body)",
            "GET /": "API documentation"
        },
        "usage": {
            "endpoint": "/predict",
            "method": "POST",
            "body": {
                "data": "[array of input records]",
                "mode": "ensemble|xgb|tft (optional)",
                "weight_tft": "0.6 (optional, for ensemble mode)"
            }
        }
    })


if __name__ == "__main__":
    logger.info(f"🚀 Starting API server on {HOST}:{PORT}")
    logger.info(f"📊 Default mode: {DEFAULT_MODE}")
    app.run(host=HOST, port=PORT, debug=False)

