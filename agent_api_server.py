"""
Agent API Server - REST API for the Hospital Agent Pipeline

Deploy this alongside your prediction API to expose agent functionality.

Endpoints:
    POST /agents/run - Run the complete agent pipeline
    GET /agents/health - Health check
    POST /agents/monitor - Run only monitor agent
    POST /agents/staffing - Run only staffing planner
    POST /agents/supplies - Run only supplies planner
    POST /agents/advisory - Run only advisory agent
"""

from flask import Flask, request, jsonify
import traceback
from datetime import datetime
import os
from typing import Dict, Any, Optional

from agents.run_pipeline import _derive_monitor_inputs
from agents.monitor_agent import run_monitor_agent
from agents.planning_agent import run_staffing_planner, run_supplies_planner
from agents.advisory_agent import run_advisory_agent
from agents.coordinator_agent import assemble_operational_plan
from agents.prediction_client import prediction_client
from agents.schemas import (
    MonitorInput,
    AgentTraceEntry,
    MonitorOutput,
    StaffingPlan,
    SuppliesPlan,
    AdvisoryOutput,
)
from agents.config import get_settings
from src.pipeline.logger import get_logger

app = Flask(__name__)
logger = get_logger(__name__)

# Configuration
PORT = int(os.getenv("PORT", "5001"))
HOST = os.getenv("HOST", "0.0.0.0")


@app.route("/agents/health", methods=["GET"])
def health():
    """Health check endpoint."""
    try:
        settings = get_settings()
        
        # Check which LLM is configured (priority order matches llm_client.py)
        import os
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        gemini_key = os.getenv("GOOGLE_API_KEY", "").strip()
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        huggingface_key = os.getenv("HUGGINGFACE_API_KEY", "").strip()
        together_key = os.getenv("TOGETHER_API_KEY", "").strip()
        
        # Determine active provider based on priority (matches llm_client.py)
        llm_provider = "ollama"  # default
        active_keys = []
        
        if groq_key:
            llm_provider = "groq"
            active_keys.append("GROQ_API_KEY")
        if gemini_key:
            if llm_provider == "ollama":
                llm_provider = "gemini"
            active_keys.append("GOOGLE_API_KEY")
        if openai_key:
            if llm_provider == "ollama":
                llm_provider = "openai"
            active_keys.append("OPENAI_API_KEY")
        if huggingface_key:
            if llm_provider == "ollama":
                llm_provider = "huggingface"
            active_keys.append("HUGGINGFACE_API_KEY")
        if together_key:
            if llm_provider == "ollama":
                llm_provider = "together"
            active_keys.append("TOGETHER_API_KEY")
        
        return jsonify({
            "status": "healthy",
            "service": "hospital-agent-api",
            "timestamp": datetime.now().isoformat(),
            "llm_provider": llm_provider,
            "active_keys": active_keys,  # Show all keys that are set
            "priority_order": "Groq > Gemini > OpenAI > Hugging Face > Together.ai > Ollama",
            "ollama_url": str(settings.ollama_base_url),
            "ollama_model": settings.ollama_model,
            "prediction_api": str(settings.prediction_api_url),
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


@app.route("/agents/run", methods=["POST"])
def run_agents():
    """
    Run the complete agent pipeline.
    
    Request Body (JSON):
    {
        "data": [
            {
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
            }
        ],
        "hospital_id": "HOSP-123",
        "disease_sensitivity": 0.5,
        "mode": "ensemble"
    }
    
    Response:
    {
        "status": "success",
        "plan": { ... operational plan ... },
        "timestamp": "2025-12-05T10:30:00"
    }
    """
    try:
        data = request.json
        
        if not data or "data" not in data:
            return jsonify({"error": "Missing 'data' field in request body"}), 400
        
        # Extract parameters
        input_data = data["data"]
        hospital_id = data.get("hospital_id", "HOSP-001")
        disease_sensitivity = float(data.get("disease_sensitivity", 0.5))
        mode = data.get("mode", "ensemble")
        
        # Prepare payload for prediction API
        payload = {
            "mode": mode,
            "data": input_data
        }
        
        logger.info(f"🤖 Running agent pipeline for hospital {hospital_id}")
        
        # Step 1: Get prediction
        predicted_inflow = prediction_client.predict(payload)
        logger.info(f"📊 Predicted inflow: {predicted_inflow}")
        
        # Step 2: Prepare monitor inputs
        record = input_data[0] if isinstance(input_data, list) else input_data
        monitor_inputs = _derive_monitor_inputs(record, disease_sensitivity)
        
        # Step 3: Run agents
        trace = [AgentTraceEntry(agent="prediction_api", message="Fetched predictions")]
        
        monitor_report = run_monitor_agent(monitor_inputs)
        trace.append(AgentTraceEntry(agent="monitor", message=f"Alert {monitor_report.alertLevel}"))
        
        staffing = run_staffing_planner(predicted_inflow)
        trace.append(AgentTraceEntry(agent="staffing_planner", message="Staffing plan ready"))
        
        supplies = run_supplies_planner(predicted_inflow)
        trace.append(AgentTraceEntry(agent="supplies_planner", message="Supplies plan ready"))
        
        advisory = run_advisory_agent(predicted_inflow, monitor_report)
        trace.append(AgentTraceEntry(agent="advisory", message="Advisory drafted"))
        
        # Step 4: Assemble final plan
        plan = assemble_operational_plan(
            hospital_id=hospital_id,
            predicted_inflow=predicted_inflow,
            monitor_report=monitor_report,
            staffing=staffing,
            supplies=supplies,
            advisory=advisory,
            trace=trace,
        )
        
        return jsonify({
            "status": "success",
            "plan": plan.model_dump(),
            "timestamp": datetime.now().isoformat()
        })
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Agent pipeline error: {e}\n{traceback.format_exc()}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route("/agents/monitor", methods=["POST"])
def run_monitor_only():
    """Run only the monitor agent."""
    try:
        data = request.json
        aqi = float(data.get("aqi", 100))
        festival_score = float(data.get("festival_score", 0))
        weather_risk = float(data.get("weather_risk", 0))
        disease_sensitivity = float(data.get("disease_sensitivity", 0.5))
        
        inputs = MonitorInput(
            aqi=aqi,
            festival_score=festival_score,
            weather_risk=weather_risk,
            disease_sensitivity=disease_sensitivity
        )
        
        result = run_monitor_agent(inputs)
        return jsonify({
            "status": "success",
            "monitor_report": result.model_dump()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/agents/staffing", methods=["POST"])
def run_staffing_only():
    """Run only the staffing planner."""
    try:
        data = request.json
        predicted_inflow = float(data.get("predicted_inflow", 200))
        
        result = run_staffing_planner(predicted_inflow)
        return jsonify({
            "status": "success",
            "staffing_plan": result.model_dump()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/agents/supplies", methods=["POST"])
def run_supplies_only():
    """Run only the supplies planner."""
    try:
        data = request.json
        predicted_inflow = float(data.get("predicted_inflow", 200))
        
        result = run_supplies_planner(predicted_inflow)
        return jsonify({
            "status": "success",
            "supplies_plan": result.model_dump()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/agents/advisory", methods=["POST"])
def run_advisory_only():
    """Run only the advisory agent."""
    try:
        data = request.json
        predicted_inflow = float(data.get("predicted_inflow", 200))
        alert_level = data.get("alert_level", "moderate")
        risk_factors = data.get("risk_factors", [])
        
        monitor_report = MonitorOutput(
            alertLevel=alert_level,
            riskFactors=risk_factors if isinstance(risk_factors, list) else [risk_factors],
            recommendedUrgency="prepare"
        )
        
        result = run_advisory_agent(predicted_inflow, monitor_report)
        return jsonify({
            "status": "success",
            "advisory": result.model_dump()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/agents", methods=["GET"])
def index():
    """API documentation endpoint."""
    return jsonify({
        "service": "Hospital Agent API",
        "version": "1.0.0",
        "endpoints": {
            "GET /agents/health": "Health check",
            "POST /agents/run": "Run complete agent pipeline",
            "POST /agents/monitor": "Run monitor agent only",
            "POST /agents/staffing": "Run staffing planner only",
            "POST /agents/supplies": "Run supplies planner only",
            "POST /agents/advisory": "Run advisory agent only",
            "GET /agents": "API documentation"
        },
        "usage": {
            "endpoint": "/agents/run",
            "method": "POST",
            "body": {
                "data": "[array of input records - same as prediction API]",
                "hospital_id": "HOSP-123",
                "disease_sensitivity": "0.5",
                "mode": "ensemble"
            }
        }
    })


if __name__ == "__main__":
    # Use Gunicorn in production (Render), Flask dev server locally
    if os.getenv("RENDER") or os.getenv("DYNO"):  # Render/Heroku detection
        # Gunicorn will be used via Procfile or start command
        logger.info(f"🚀 Production mode - Gunicorn will start the server")
    else:
        logger.info(f"🚀 Starting Agent API server on {HOST}:{PORT}")
        app.run(host=HOST, port=PORT, debug=False)

