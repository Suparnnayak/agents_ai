# 🚀 Render Deployment Guide - Agent API

Step-by-step guide to deploy your agent system on Render.

## 📋 Prerequisites

1. ✅ GitHub repository with your code
2. ✅ Render account (sign up at https://render.com)
3. ✅ Prediction API already deployed (or use: https://ai-health-agent-vuol.onrender.com/predict)

## 🎯 Step-by-Step Deployment

### Step 1: Prepare Your Repository

Make sure these files are in your repo:
- ✅ `agent_api_server.py`
- ✅ `render_agents.yaml`
- ✅ `requirements.txt`
- ✅ `agents/` folder (all agent files)
- ✅ `src/` folder (for logger)

### Step 2: Push to GitHub

```bash
# Make sure all files are committed
git add agent_api_server.py render_agents.yaml requirements.txt
git commit -m "Add agent API server for Render deployment"
git push origin main
```

### Step 3: Create New Web Service on Render

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Click "New +"** → **"Web Service"**
3. **Connect your GitHub repository**
   - If first time: Authorize Render to access GitHub
   - Select your repository
   - Click "Connect"

### Step 4: Configure Service

Render will auto-detect `render_agents.yaml`. If not, configure manually:

**Basic Settings:**
- **Name**: `hospital-agent-api` (or your choice)
- **Environment**: `Python 3`
- **Region**: Choose closest to you
- **Branch**: `main` (or your default branch)

**Build & Deploy:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python agent_api_server.py`

**Advanced Settings:**
- **Health Check Path**: `/agents/health`
- **Plan**: 
  - **Free** (spins down after inactivity) - Good for testing
  - **Starter ($7/month)** - Always running, recommended for production

### Step 5: Set Environment Variables

In Render dashboard, go to **Environment** tab and add:

```bash
# Required
AGENT_PREDICTION_API_URL=https://ai-health-agent-vuol.onrender.com/predict

# Ollama Configuration (choose one option below)
```

**Option A: Use Cloud LLM (Recommended - No Ollama needed)**

```bash
# Use Together.ai (cheap, $0.0001 per request)
TOGETHER_API_KEY=your_together_api_key_here
AGENT_OLLAMA_BASE_URL=
AGENT_OLLAMA_MODEL=

# OR use OpenAI
OPENAI_API_KEY=sk-your_openai_key_here
AGENT_OLLAMA_BASE_URL=
AGENT_OLLAMA_MODEL=
```

**Option B: Deploy Ollama Separately (Advanced)**

If you want to use Ollama, you need to:
1. Deploy Ollama as a separate service on Render
2. Set `AGENT_OLLAMA_BASE_URL` to that service URL
3. This requires more resources (Starter plan minimum)

**Option C: Use External Ollama Service**

If you have Ollama running elsewhere:
```bash
AGENT_OLLAMA_BASE_URL=https://your-ollama-service.com
AGENT_OLLAMA_MODEL=phi3
AGENT_TEMPERATURE=0.1
```

**For now, let's use Option A (Cloud LLM) - it's easier!**

### Step 6: Deploy

1. **Click "Create Web Service"**
2. **Wait for build** (takes 2-5 minutes)
3. **Check logs** for any errors

### Step 7: Test Your Deployment

Once deployed, you'll get a URL like: `https://hospital-agent-api.onrender.com`

**Test Health Endpoint:**
```bash
curl https://hospital-agent-api.onrender.com/agents/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "hospital-agent-api",
  "timestamp": "2025-12-05T10:30:00",
  "prediction_api": "https://ai-health-agent-vuol.onrender.com/predict"
}
```

**Test Full Pipeline:**
```bash
curl -X POST https://hospital-agent-api.onrender.com/agents/run \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```

## 🔧 Using Cloud LLM (Recommended)

Since Render free tier doesn't include Ollama, use a cloud LLM service:

### Option 1: Together.ai (Cheapest - $0.0001/request)

1. **Sign up**: https://together.ai
2. **Get API key** from dashboard
3. **Update `agents/llm_client.py`** to use Together:

```python
# Add to agents/llm_client.py
from langchain_together import Together

class LLMClient:
    def __init__(self):
        settings = get_settings()
        api_key = os.getenv("TOGETHER_API_KEY")
        
        if api_key:
            # Use Together.ai
            self.llm = Together(
                model="meta-llama/Llama-3-8b-chat-hf",
                together_api_key=api_key,
                temperature=settings.temperature
            )
        else:
            # Fallback to Ollama
            self.llm = Ollama(
                model=settings.ollama_model,
                temperature=settings.temperature,
                base_url=settings.ollama_base_url,
            )
```

4. **Set environment variable**:
```bash
TOGETHER_API_KEY=your_key_here
```

### Option 2: OpenAI (More reliable)

1. **Get API key** from https://platform.openai.com
2. **Update `agents/llm_client.py`**:

```python
from langchain_openai import ChatOpenAI

class LLMClient:
    def __init__(self):
        settings = get_settings()
        api_key = os.getenv("OPENAI_API_KEY")
        
        if api_key:
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=settings.temperature,
                api_key=api_key
            )
        else:
            # Fallback to Ollama
            self.llm = Ollama(...)
```

3. **Set environment variable**:
```bash
OPENAI_API_KEY=sk-your_key_here
```

## 📝 Quick Setup Checklist

- [ ] Code pushed to GitHub
- [ ] Render account created
- [ ] New Web Service created
- [ ] Environment variables set:
  - [ ] `AGENT_PREDICTION_API_URL`
  - [ ] `TOGETHER_API_KEY` or `OPENAI_API_KEY` (if using cloud LLM)
  - [ ] `AGENT_OLLAMA_BASE_URL` (if using Ollama)
  - [ ] `AGENT_OLLAMA_MODEL` (if using Ollama)
- [ ] Service deployed successfully
- [ ] Health check passes
- [ ] Test full pipeline

## 🐛 Troubleshooting

### Build Fails

**Error**: `ModuleNotFoundError`
**Solution**: Check `requirements.txt` includes all dependencies

**Error**: `ImportError: cannot import name 'X'`
**Solution**: Make sure all files are in the repo, check file paths

### Service Won't Start

**Error**: `Port already in use`
**Solution**: Render sets PORT automatically, don't hardcode it

**Error**: `Connection refused to Ollama`
**Solution**: Use cloud LLM instead, or deploy Ollama separately

### Health Check Fails

**Error**: `404 Not Found`
**Solution**: Check health check path is `/agents/health`

**Error**: `500 Internal Server Error`
**Solution**: Check logs in Render dashboard for details

### API Timeout

**Error**: `ReadTimeout`
**Solution**: 
- Prediction API may be sleeping (free tier)
- Use UptimeRobot to keep prediction API alive
- Or upgrade to Starter plan

## 🔄 Updating Your Deployment

After making changes:

1. **Push to GitHub**:
```bash
git add .
git commit -m "Update agent API"
git push
```

2. **Render auto-deploys** (if auto-deploy is enabled)
3. **Or manually deploy** from Render dashboard

## 📊 Monitoring

### View Logs

1. Go to Render dashboard
2. Select your service
3. Click "Logs" tab
4. See real-time logs

### Health Monitoring

Set up UptimeRobot to ping `/agents/health` every 5 minutes to keep service alive (free tier).

## 💰 Cost Estimate

- **Free Tier**: $0/month (spins down after inactivity)
- **Starter Plan**: $7/month (always running)
- **Together.ai**: ~$0.01/month (very cheap, pay per use)
- **OpenAI**: ~$0.10/month (pay per use)

**Recommended**: Free tier + Together.ai = ~$0.01/month total

## ✅ Next Steps

Once deployed:

1. ✅ Test all endpoints
2. ✅ Set up UptimeRobot to keep service alive
3. ✅ Document your API URL
4. ✅ Test with real data
5. ✅ Set up automation (we'll do this later!)

## 📞 Need Help?

- Check Render logs for errors
- Verify environment variables are set
- Test locally first: `python agent_api_server.py`
- Check `README_AGENTS.md` for more details

---

**Ready to deploy?** Follow the steps above and you'll have your agent API live in 10 minutes! 🚀

