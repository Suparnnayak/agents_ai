# 🚀 Render Deployment Guide

Complete guide to deploy your Hospital Admissions Forecast API on Render.

## 📋 Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Push your code to GitHub (recommended)
3. **Model Files**: Ensure all model files are in `models/` directory

## 🚀 Quick Deployment (5 minutes)

### **Method 1: Using Render Dashboard (Recommended)**

1. **Login to Render Dashboard**
   - Go to [dashboard.render.com](https://dashboard.render.com)
   - Click "New +" → "Web Service"

2. **Connect Repository**
   - Connect your GitHub repository
   - Or use "Public Git repository" and paste your repo URL

3. **Configure Service**
   - **Name**: `hospital-forecast-api` (or your choice)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python api_server.py`
   - **Plan**: Choose `Starter` (free) or `Standard`/`Pro` for production

4. **Environment Variables** (Optional)
   - Click "Advanced" → "Environment Variables"
   - Add if needed:
     ```
     PREDICTION_MODE=ensemble
     TFT_WEIGHT=0.6
     ```

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy

### **Method 2: Using render.yaml (Infrastructure as Code)**

1. **Push render.yaml to your repository**
   - The `render.yaml` file is already created in your project

2. **Deploy via Render Dashboard**
   - Go to Render Dashboard
   - Click "New +" → "Blueprint"
   - Connect your repository
   - Render will automatically detect `render.yaml` and create the service

## 📁 Required Files for Render

Your repository should have:

```
.
├── api_server.py          # ✅ Main API server
├── requirements.txt       # ✅ Python dependencies
├── Procfile              # ✅ Process file (optional, but recommended)
├── render.yaml           # ✅ Render config (optional)
├── models/               # ✅ Model files (must be in repo or uploaded)
│   ├── global_q10.json
│   ├── global_q50.json
│   ├── global_q90.json
│   ├── global_q50_spike.json
│   ├── global_q50_extreme_spike.json
│   └── tft_global_q50.pth
└── src/                  # ✅ Source code
```

## ⚙️ Configuration

### **Environment Variables**

Set these in Render Dashboard → Your Service → Environment:

| Variable | Default | Description |
|----------|---------|-------------|
| `PREDICTION_MODE` | `ensemble` | `xgb`, `tft`, or `ensemble` |
| `TFT_WEIGHT` | `0.6` | TFT weight in ensemble (0-1) |
| `PORT` | Auto-set | Port (Render sets this automatically) |
| `HOST` | `0.0.0.0` | Host (default is fine) |

### **Build Settings**

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python api_server.py`
- **Python Version**: `3.10` or `3.11` (specify in `runtime.txt` if needed)

## 📝 Step-by-Step Deployment

### **Step 1: Prepare Your Repository**

```bash
# Ensure all files are committed
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

### **Step 2: Create Web Service on Render**

1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select your repository

### **Step 3: Configure Service**

**Basic Settings:**
- **Name**: `hospital-forecast-api`
- **Region**: Choose closest to your users
- **Branch**: `main` (or your default branch)
- **Root Directory**: Leave empty (or `.` if needed)

**Build & Deploy:**
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python api_server.py`

**Plan:**
- **Free**: Good for testing (spins down after inactivity)
- **Starter ($7/mo)**: Always on, 512MB RAM
- **Standard ($25/mo)**: 2GB RAM, better performance
- **Pro ($85/mo)**: 4GB RAM, production-grade

### **Step 4: Add Environment Variables (Optional)**

Go to **Environment** tab and add:
```
PREDICTION_MODE=ensemble
TFT_WEIGHT=0.6
```

### **Step 5: Deploy**

Click **"Create Web Service"** and wait for deployment.

## 🔍 Verify Deployment

### **1. Check Build Logs**

In Render Dashboard → Your Service → **Logs**:
- Should see: `✅ Loaded XGBoost model from models\global_q50.json`
- Should see: `🚀 Starting API server on 0.0.0.0:XXXX`

### **2. Test Health Endpoint**

```bash
curl https://your-service-name.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "hospital-admissions-forecast",
  "timestamp": "2025-11-28T..."
}
```

### **3. Test Prediction Endpoint**

```bash
curl -X POST https://your-service-name.onrender.com/predict \
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
    }]
  }'
```

## ⚠️ Important Considerations

### **1. Model Files Size**

Your model files might be large:
- XGBoost models: ~5-10 MB each
- TFT model: ~50-100 MB
- **Total**: ~100-200 MB

**Solutions:**
- ✅ Render free tier allows up to 500 MB
- ✅ Use Git LFS for large files (if needed)
- ✅ Or upload models to cloud storage and download on startup

### **2. Free Tier Limitations**

- **Spins down after 15 minutes of inactivity**
- **Takes 30-60 seconds to wake up** (cold start)
- **512 MB RAM** (may need Starter plan for TFT model)

**Recommendation**: Use **Starter plan ($7/mo)** for production to avoid cold starts.

### **3. Memory Requirements**

- **XGBoost only**: ~200-300 MB RAM ✅ (works on free tier)
- **Ensemble (XGB + TFT)**: ~500-800 MB RAM ⚠️ (needs Starter plan)

**If memory issues:**
- Use `PREDICTION_MODE=xgb` (no TFT, less memory)
- Upgrade to Starter/Standard plan

### **4. Build Time**

First deployment may take 5-10 minutes:
- Installing dependencies (PyTorch, XGBoost, etc.)
- Loading model files

Subsequent deployments are faster (2-3 minutes).

## 🔧 Troubleshooting

### **Issue: Build Fails**

**Check:**
1. `requirements.txt` exists and is correct
2. Python version compatibility
3. Build logs for specific errors

**Fix:**
```bash
# Create runtime.txt to specify Python version
echo "python-3.10" > runtime.txt
```

### **Issue: Service Crashes on Start**

**Check logs for:**
- Missing model files
- Import errors
- Port binding issues

**Common fixes:**
- Ensure `models/` directory is in repository
- Check all dependencies in `requirements.txt`
- Verify `api_server.py` uses `os.getenv("PORT")`

### **Issue: Out of Memory**

**Symptoms:**
- Service crashes during prediction
- "Killed" messages in logs

**Solutions:**
1. Use `PREDICTION_MODE=xgb` (no TFT)
2. Upgrade to Starter/Standard plan
3. Reduce batch size in requests

### **Issue: Slow Response Times**

**Causes:**
- Cold start (free tier)
- Large model loading
- Memory constraints

**Solutions:**
- Upgrade to Starter plan (always on)
- Use XGB-only mode for faster predictions
- Implement model caching (load once at startup)

## 📊 Monitoring

### **Render Dashboard**

- **Metrics**: CPU, Memory, Response Time
- **Logs**: Real-time application logs
- **Events**: Deployments, restarts, errors

### **Health Check**

Render automatically pings `/health` endpoint:
- Configured in `render.yaml`: `healthCheckPath: /health`
- Service marked unhealthy if health check fails

## 🔒 Security (Optional)

### **Add API Key Authentication**

1. Set environment variable: `API_KEY=your-secret-key`
2. Update `api_server.py` (see DEPLOYMENT_GUIDE.md for code)

### **Rate Limiting**

Add to `requirements.txt`:
```
flask-limiter>=3.0.0
```

## 📈 Scaling

### **Horizontal Scaling**

Render supports:
- **Multiple instances** (Standard/Pro plans)
- **Auto-scaling** based on traffic
- **Load balancing** (automatic)

### **Vertical Scaling**

Upgrade plan:
- **Starter**: 512 MB RAM, 0.5 CPU
- **Standard**: 2 GB RAM, 1 CPU
- **Pro**: 4 GB RAM, 2 CPU

## 💰 Cost Estimation

- **Free**: $0 (with limitations)
- **Starter**: $7/month (recommended for production)
- **Standard**: $25/month (high traffic)
- **Pro**: $85/month (enterprise)

## ✅ Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] `requirements.txt` includes all dependencies
- [ ] `models/` directory with all model files
- [ ] `api_server.py` uses `os.getenv("PORT")`
- [ ] Tested locally (`python api_server.py`)
- [ ] Environment variables configured (optional)
- [ ] Health check endpoint working
- [ ] Prediction endpoint tested
- [ ] Monitoring set up

## 🎉 Post-Deployment

After successful deployment:

1. **Save your service URL**: `https://your-service.onrender.com`
2. **Test all endpoints**: `/health`, `/predict`, `/`
3. **Monitor logs** for first few requests
4. **Set up alerts** (if using paid plan)
5. **Update your agent** with the new API URL

## 📞 Support

- **Render Docs**: [render.com/docs](https://render.com/docs)
- **Render Status**: [status.render.com](https://status.render.com)
- **Community**: [community.render.com](https://community.render.com)

---

**Your API will be live at**: `https://your-service-name.onrender.com` 🚀

