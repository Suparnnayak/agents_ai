# ⚡ Render Quick Start (5 Minutes)

## 🚀 Fastest Deployment Path

### **Step 1: Push to GitHub**

```bash
git add .
git commit -m "Ready for Render"
git push origin main
```

### **Step 2: Deploy on Render**

1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select your repo

### **Step 3: Configure**

**Settings:**
- **Name**: `hospital-forecast-api`
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python api_server.py`
- **Plan**: `Starter` ($7/mo) or `Free` (for testing)

### **Step 4: Deploy**

Click **"Create Web Service"** → Wait 5-10 minutes → Done! ✅

## 📝 Important Notes

### **Model Files**

✅ **Make sure `models/` directory is in your Git repository:**
```bash
# Check if models are tracked
git ls-files models/

# If not, add them:
git add models/
git commit -m "Add model files"
git push
```

### **Free Tier Warning**

⚠️ **Free tier spins down after 15 min inactivity**
- First request after spin-down: 30-60 second delay
- **Solution**: Use Starter plan ($7/mo) for always-on

### **Memory Requirements**

- **XGB-only mode**: Works on free tier ✅
- **Ensemble mode (XGB+TFT)**: Needs Starter plan ⚠️

**If memory issues, set environment variable:**
```
PREDICTION_MODE=xgb
```

## 🧪 Test After Deployment

```bash
# Health check
curl https://your-service.onrender.com/health

# Prediction
curl -X POST https://your-service.onrender.com/predict \
  -H "Content-Type: application/json" \
  -d '{"data": [{"date": "2025-11-29", "admissions": 150, "aqi": 180, "temp": 28.5, "humidity": 65, "rainfall": 12.3, "wind_speed": 15.2, "mobility_index": 75, "outbreak_index": 30, "festival_flag": 0, "holiday_flag": 0, "weekday": 4, "is_weekend": 0, "population_density": 12000, "hospital_beds": 500, "staff_count": 200, "city_id": 1, "hospital_id_enc": 101}]}'
```

## 📚 Full Guide

See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for detailed instructions.

---

**Your API URL**: `https://your-service-name.onrender.com` 🎉

