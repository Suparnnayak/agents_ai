# ⚡ Quick Start: Deploy Agents on Render (5 Minutes)

## 🎯 What You'll Deploy

A REST API that runs your 4 agents and returns operational plans.

## 📋 Prerequisites Checklist

- [ ] Code is on GitHub
- [ ] Render account (sign up at https://render.com - free)
- [ ] Prediction API URL (use: `https://ai-health-agent-vuol.onrender.com/predict`)

## 🚀 5-Minute Deployment

### Step 1: Push Code to GitHub (1 min)

```bash
# Make sure these files exist:
# - agent_api_server.py
# - render_agents.yaml
# - requirements.txt
# - agents/ folder

git add .
git commit -m "Ready for Render deployment"
git push
```

### Step 2: Create Render Service (2 min)

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repo
4. Render will auto-detect `render_agents.yaml` ✅

### Step 3: Set Environment Variables (1 min)

In Render dashboard → **Environment** tab, add:

```bash
# Required
AGENT_PREDICTION_API_URL=https://ai-health-agent-vuol.onrender.com/predict

# Choose ONE option below:
```

**Option A: Together.ai (Recommended - Cheapest)**
```bash
TOGETHER_API_KEY=your_together_api_key
```
Get key: https://together.ai (free tier available)

**Option B: OpenAI**
```bash
OPENAI_API_KEY=sk-your_openai_key
```
Get key: https://platform.openai.com

**Option C: Use Ollama (if you have it deployed)**
```bash
AGENT_OLLAMA_BASE_URL=https://your-ollama-service.com
AGENT_OLLAMA_MODEL=phi3
AGENT_TEMPERATURE=0.1
```

### Step 4: Deploy (1 min)

1. Click **"Create Web Service"**
2. Wait 2-3 minutes for build
3. Get your URL: `https://your-app.onrender.com`

### Step 5: Test (30 sec)

```bash
# Test health
curl https://your-app.onrender.com/agents/health

# Test full pipeline
curl -X POST https://your-app.onrender.com/agents/run \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```

## ✅ Done!

Your agent API is now live! 🎉

## 🔧 Quick Setup: Together.ai (Free)

1. **Sign up**: https://together.ai
2. **Get API key** from dashboard
3. **Add to Render**: `TOGETHER_API_KEY=your_key`
4. **Done!** No Ollama needed!

**Cost**: ~$0.0001 per request (very cheap!)

## 📝 What's Next?

- ✅ Test all endpoints
- ✅ Set up UptimeRobot to keep service alive (free tier)
- ✅ Document your API URL
- ✅ Later: Set up automation

## 🐛 Quick Fixes

**Build fails?**
- Check `requirements.txt` has all dependencies
- Check logs in Render dashboard

**Service won't start?**
- Check environment variables are set
- Check logs for errors

**API timeout?**
- Prediction API may be sleeping
- Use UptimeRobot to keep it alive

---

**Need detailed guide?** See `RENDER_AGENTS_DEPLOYMENT.md`

