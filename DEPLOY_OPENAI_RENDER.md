# 🚀 Deploy Agents on Render with OpenAI - Step-by-Step Guide

Complete guide to deploy your agent API on Render using OpenAI.

## 📋 Prerequisites Checklist

- [ ] GitHub repository with your code
- [ ] Render account (sign up at https://render.com - free)
- [ ] OpenAI account (sign up at https://platform.openai.com - get $5 free credit)

---

## 🎯 Step 1: Get OpenAI API Key (2 minutes)

1. **Go to**: https://platform.openai.com
2. **Sign up** or log in
3. **Get $5 free credit** (for new users)
4. **Navigate to**: API Keys section (left sidebar)
5. **Click**: "Create new secret key"
6. **Name it**: "Hospital Agent API" (optional)
7. **Copy the key** - it looks like: `sk-...` 
   - ⚠️ **Important**: Copy it now! You won't see it again.
8. **Save it somewhere safe** (you'll need it in Step 4)

---

## 🎯 Step 2: Push Code to GitHub (1 minute)

Make sure all your code is pushed to GitHub:

```bash
# Check what needs to be committed
git status

# Add all files
git add .

# Commit
git commit -m "Ready for Render deployment with OpenAI"

# Push to GitHub
git push origin main
```

**Verify**: Go to your GitHub repo and check these files exist:
- ✅ `agent_api_server.py`
- ✅ `render_agents.yaml`
- ✅ `requirements.txt`
- ✅ `agents/` folder
- ✅ `src/` folder

---

## 🎯 Step 3: Deploy on Render (5 minutes)

### 3.1 Create New Web Service

1. **Go to**: https://dashboard.render.com
2. **Sign up** if you don't have an account (free)
3. **Click**: "New +" button (top right)
4. **Select**: "Web Service"

### 3.2 Connect GitHub Repository

1. **Click**: "Connect GitHub" (or "Connect GitLab" if using GitLab)
2. **Authorize Render** (if first time):
   - Click "Authorize render"
   - Grant access to your repositories
3. **Select your repository** from the list
4. **Click**: "Connect"

### 3.3 Configure Service

Render should **auto-detect** `render_agents.yaml`. If it does:

✅ **Name**: `hospital-agent-api` (or your choice)
✅ **Region**: Choose closest to you
✅ **Branch**: `main` (or your default branch)
✅ **Build Command**: `pip install -r requirements.txt` (auto-filled)
✅ **Start Command**: `python agent_api_server.py` (auto-filled)

If it doesn't auto-detect, manually enter:
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python agent_api_server.py`

### 3.4 Set Environment Variables

**Scroll down to "Environment" section** and add these variables:

**Click "Add Environment Variable" for each:**

1. **Required - Prediction API:**
   ```
   Key: AGENT_PREDICTION_API_URL
   Value: https://ai-health-agent-vuol.onrender.com/predict
   ```

2. **Required - OpenAI:**
   ```
   Key: OPENAI_API_KEY
   Value: sk-your_openai_key_here
   ```
   (Paste the key you copied in Step 1)

3. **Optional - Model (defaults to gpt-3.5-turbo):**
   ```
   Key: AGENT_OLLAMA_MODEL
   Value: (leave empty or remove)
   ```

4. **Optional - Temperature:**
   ```
   Key: AGENT_TEMPERATURE
   Value: 0.1
   ```

### 3.5 Choose Plan

- **Free** (for testing) - Spins down after 15 min inactivity
- **Starter ($7/month)** - Always running (recommended for production)

**For now, choose Free** (you can upgrade later).

### 3.6 Deploy

1. **Click**: "Create Web Service"
2. **Wait**: 2-5 minutes for build
3. **Watch logs**: You'll see build progress
4. **Success**: You'll see "Your service is live" message

---

## 🎯 Step 4: Test Your Deployment (1 minute)

Once deployed, you'll get a URL like: `https://hospital-agent-api.onrender.com`

### Test Health Endpoint

```bash
curl https://your-app.onrender.com/agents/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "hospital-agent-api",
  "timestamp": "2025-12-05T10:30:00",
  "ollama_url": "http://localhost:11434",
  "ollama_model": "phi3",
  "prediction_api": "https://ai-health-agent-vuol.onrender.com/predict"
}
```

### Test Full Pipeline

```bash
curl -X POST https://your-app.onrender.com/agents/run \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```

**Expected Response:**
```json
{
  "status": "success",
  "plan": {
    "requestId": "...",
    "predictedInflow": 250.5,
    "monitorReport": {...},
    "staffingPlan": {...},
    "suppliesPlan": {...},
    "advisory": {...}
  }
}
```

---

## 🎯 Step 5: Keep Service Alive (2 minutes) ⚠️

**Important for Free Tier**: Set up UptimeRobot to keep service alive

1. **Go to**: https://uptimerobot.com
2. **Sign up** (free account)
3. **Click**: "Add New Monitor"
4. **Configure**:
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `Hospital Agent API`
   - **URL**: `https://your-app.onrender.com/agents/health`
   - **Monitoring Interval**: `5 minutes`
5. **Click**: "Create Monitor"
6. **Done!** ✅ Service will stay alive

**Also set up for Prediction API:**
- Add another monitor for: `https://ai-health-agent-vuol.onrender.com/health`
- Same settings

---

## ✅ Deployment Checklist

Before starting:
- [ ] OpenAI account created
- [ ] OpenAI API key copied
- [ ] Code pushed to GitHub
- [ ] Render account created

During deployment:
- [ ] Web service created on Render
- [ ] GitHub repo connected
- [ ] Environment variables set:
  - [ ] `AGENT_PREDICTION_API_URL`
  - [ ] `OPENAI_API_KEY`
- [ ] Service deployed successfully

After deployment:
- [ ] Health endpoint works (`/agents/health`)
- [ ] Full pipeline test passes (`/agents/run`)
- [ ] UptimeRobot monitors set up
- [ ] API URL saved/documentation

---

## 🐛 Troubleshooting

### Build Fails

**Error**: `ModuleNotFoundError: No module named 'langchain'`
**Solution**: 
- Check `requirements.txt` has all dependencies
- Check Render logs for specific error
- Make sure `langchain-openai` is in requirements (it's optional, but install if needed)

**Error**: `ImportError: cannot import name 'X'`
**Solution**: 
- Verify all files are in GitHub repo
- Check file paths are correct
- Check Render logs for specific import error

### Service Won't Start

**Error**: `Port already in use`
**Solution**: 
- Render sets PORT automatically
- Don't hardcode port in code
- Check `agent_api_server.py` uses `os.getenv("PORT")`

**Error**: `Connection refused to Ollama`
**Solution**: 
- This is normal! You're using OpenAI, not Ollama
- The error is harmless (it's just the fallback)
- Check logs - you should see "✅ Using OpenAI for LLM"

### OpenAI Connection Error

**Error**: `Invalid API key`
**Solution**: 
- Check API key is correct (starts with `sk-`)
- No extra spaces before/after key
- Key is active in OpenAI dashboard

**Error**: `Insufficient quota`
**Solution**: 
- Check OpenAI dashboard for credit balance
- Free tier has $5 credit
- Upgrade if needed

### Health Check Fails

**Error**: `404 Not Found`
**Solution**: 
- Check health check path is `/agents/health`
- Verify service is running (check logs)
- Check URL is correct

**Error**: `500 Internal Server Error`
**Solution**: 
- Check Render logs for specific error
- Verify environment variables are set
- Check OpenAI API key is valid

---

## 📊 Monitoring

### View Logs

1. Go to Render dashboard
2. Select your service
3. Click "Logs" tab
4. See real-time logs

### Check OpenAI Usage

1. Go to https://platform.openai.com
2. Navigate to "Usage" section
3. See API usage and remaining credits

---

## 💰 Cost Estimate

- **Render Free Tier**: $0/month (spins down after inactivity)
- **Render Starter**: $7/month (always running)
- **OpenAI**: 
  - $5 free credit (for new users)
  - ~$0.002 per request after free credit
  - ~2500 requests with free credit

**Total for testing**: **$0** (free tier + free credit)

**Total for production**: **~$7-10/month** (Starter plan + minimal OpenAI usage)

---

## 🔄 Updating Your Deployment

After making code changes:

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Update agent API"
   git push
   ```

2. **Render auto-deploys** (if auto-deploy is enabled)
3. **Or manually deploy** from Render dashboard → "Manual Deploy"

---

## 📝 Environment Variables Summary

**Required:**
```bash
AGENT_PREDICTION_API_URL=https://ai-health-agent-vuol.onrender.com/predict
OPENAI_API_KEY=sk-your_openai_key_here
```

**Optional:**
```bash
AGENT_TEMPERATURE=0.1
PORT=10000  # Auto-set by Render, don't override
```

---

## 🎯 Next Steps After Deployment

1. ✅ **Test all endpoints**
2. ✅ **Set up UptimeRobot** to keep service alive
3. ✅ **Document your API URL**
4. ✅ **Test with real data**
5. ⏭️ **Set up automation** (we'll do this next!)

---

## 📞 Need Help?

- **Check Render logs** for errors
- **Verify environment variables** are set correctly
- **Test locally first**: `python agent_api_server.py`
- **Check OpenAI dashboard** for API key status

---

## 🚀 Quick Command Reference

```bash
# Test health
curl https://your-app.onrender.com/agents/health

# Test full pipeline
curl -X POST https://your-app.onrender.com/agents/run \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json

# Test individual agents
curl -X POST https://your-app.onrender.com/agents/monitor \
  -H "Content-Type: application/json" \
  -d '{"aqi": 240, "festival_score": 1.0, "weather_risk": 0.3, "disease_sensitivity": 0.5}'
```

---

**Ready?** Follow the steps above and you'll have your agent API live in 10 minutes! 🎉

