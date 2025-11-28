# Agent Data Flow Guide

## Overview
All **4 agents** are fully implemented and working:
1. **Monitor Agent** - Evaluates environmental risks
2. **Staffing Planner** - Plans staff requirements
3. **Supplies Planner** - Plans medical supplies
4. **Advisory Agent** - Generates public/clinical guidance
5. **Coordinator** - Aggregates all outputs

## Data Flow

### Input Fields (NOT Static - Can Be Changed!)

Your `sample_request.json` contains dynamic values that affect all agents:

```json
{
  "temp": 26.0,           // Used for weather_risk calculation
  "aqi": 240,             // Direct input to Monitor Agent
  "rainfall": 5.0,         // Used for weather_risk calculation
  "humidity": 70,          // Used for weather_risk calculation
  "festival_flag": 1,      // Converted to festival_score for Monitor
  "admissions": 210,       // Historical data for ML model
  // ... other fields for ML prediction
}
```

### How Each Field Is Used

#### 1. **Temperature (`temp`)**
- **Used in**: Weather risk calculation
- **Formula**: `max(temp - 35, 0) / 25.0` (higher temp = higher risk)
- **Affects**: Monitor Agent → Alert Level → Advisory Agent

#### 2. **AQI (`aqi`)**
- **Used in**: Monitor Agent (direct input)
- **Effect**: High AQI (>200) triggers higher alert levels
- **Affects**: Monitor Agent → Advisory Agent (pollution care guidance)

#### 3. **Rainfall (`rainfall`)**
- **Used in**: Weather risk calculation
- **Formula**: `rainfall / 60.0` (more rain = higher risk)
- **Affects**: Monitor Agent → Weather risk assessment

#### 4. **Humidity (`humidity`)**
- **Used in**: Weather risk calculation
- **Formula**: `(humidity - 70) / 40.0` (high humidity = higher risk)
- **Affects**: Monitor Agent → Weather risk assessment

#### 5. **Festival Flag (`festival_flag`)**
- **Used in**: Festival score (0 or 1)
- **Effect**: Festivals increase patient inflow risk
- **Affects**: Monitor Agent → Alert level

#### 6. **All Fields → ML Model**
- All fields are sent to the prediction API
- Returns `predicted_inflow` (median forecast)
- **Used by**: Staffing Planner, Supplies Planner, Advisory Agent

### Agent Pipeline Flow

```
Input JSON
    ↓
┌─────────────────────────────────────┐
│ 1. Prediction API (ML Model)        │
│    Input: All fields                │
│    Output: predicted_inflow         │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 2. Monitor Agent                    │
│    Input: AQI, weather_risk,        │
│          festival_score,            │
│          disease_sensitivity        │
│    Output: alertLevel, riskFactors, │
│           recommendedUrgency        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 3. Staffing Planner                 │
│    Input: predicted_inflow          │
│    Output: doctorsNeeded,          │
│           nursesNeeded,            │
│           supportStaffNeeded        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 4. Supplies Planner                 │
│    Input: predicted_inflow          │
│    Output: oxygenCylinders, beds,  │
│           commonMedicines,         │
│           specialMedicines         │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 5. Advisory Agent                   │
│    Input: predicted_inflow,         │
│          monitor_report              │
│    Output: publicAdvisory,          │
│           triageRules,             │
│           teleconsultation,         │
│           pollutionCare             │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 6. Coordinator                      │
│    Aggregates all outputs           │
│    Generates recommendedActions     │
└─────────────────────────────────────┘
```

## Example Scenarios

### Scenario 1: High Pollution Day
```json
{
  "aqi": 350,        // Very high pollution
  "temp": 38.0,      // Hot day
  "rainfall": 0.0,
  "festival_flag": 0
}
```
**Expected**: High alert level, focus on respiratory care, more oxygen cylinders

### Scenario 2: Festival Season
```json
{
  "aqi": 180,
  "temp": 28.0,
  "festival_flag": 1,  // Festival active
  "rainfall": 2.0
}
```
**Expected**: Moderate-high alert, increased staffing needs

### Scenario 3: Extreme Weather
```json
{
  "aqi": 120,
  "temp": 42.0,      // Extreme heat
  "rainfall": 45.0,   // Heavy rain
  "humidity": 85,     // High humidity
  "festival_flag": 0
}
```
**Expected**: High alert, weather-related risk factors

## Usage

Change any values in your JSON file and run:

```bash
python -m agents.run_pipeline \
  --payload-file samples/sample_request.json \
  --hospital-id HOSP-123 \
  --disease-sensitivity 0.7
```

All agents will automatically adapt to the new values!

