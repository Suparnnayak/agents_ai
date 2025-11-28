# ✅ Agent Deployment Checklist - Render

## 📦 What's Ready

✅ **Agent API Server** (`agent_api_server.py`) - REST API for all 4 agents
✅ **Render Config** (`render_agents.yaml`) - Auto-detected by Render
✅ **LLM Client** - Updated to support Ollama, OpenAI, or Together.ai
✅ **Requirements** - All dependencies listed
✅ **Documentation** - Step-by-step guides created

## 🚀 Deployment Steps

### 1. Choose LLM Option

**Option A: Together.ai (Recommended - Easiest)**
- ✅ Sign up: https://together.ai
- ✅ Get API key
- ✅ Add to Render: `TOGETHER_API_KEY=your_key`
- ✅ Install: `pip install langchain-together` (or add to requirements.txt)
- 💰 Cost: ~$0.0001 per request

**Option B: OpenAI**
- ✅ Get API key: https://platform.openai.com
- ✅ Add to Render: `OPENAI_API_KEY=sk-your_key`
- ✅ Install: `pip install langchain-openai`
- 💰 Cost: ~$0.002 per request

**Option C: Ollama (Advanced)**
- ⚠️ Need to deploy Ollama separately on Render
- ⚠️ Requires more resources (Starter plan minimum)
- ✅ Set: `AGENT_OLLAMA_BASE_URL=https://your-ollama-service.com`

### 2. Push to GitHub

```bash
# Make sure all files are committed
git status

# Add any new files
git add agent_api_server.py render_agents.yaml
git add agents/llm_client.py requirements.txt

# Commit
git commit -m "Ready for Render deployment - Agent API"

# Push
git push origin main
```

### 3. Deploy on Render

1. **Go to**: https://dashboard.render.com
2. **Click**: "New +" → "Web Service"
3. **Connect**: Your GitHub repository
4. **Render will auto-detect**: `render_agents.yaml` ✅
5. **Set Environment Variables**:
   ```
   AGENT_PREDICTION_API_URL=https://ai-health-agent-vuol.onrender.com/predict
   TOGETHER_API_KEY=your_key_here  # If using Together.ai
   ```
6. **Click**: "Create Web Service"
7. **Wait**: 2-5 minutes for build

### 4. Test Deployment

```bash
# Get your URL (e.g., https://hospital-agent-api.onrender.com)

# Test health
curl https://your-app.onrender.com/agents/health

# Test full pipeline
curl -X POST https://your-app.onrender.com/agents/run \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```

### 5. Keep Service Alive (Free Tier)

**Set up UptimeRobot:**
1. Go to https://uptimerobot.com
2. Add monitor:
   - URL: `https://your-app.onrender.com/agents/health`
   - Interval: 5 minutes
3. Done! Service stays alive ✅

## 📝 Files to Check

Before deploying, verify these exist:

- [ ] `agent_api_server.py`
- [ ] `render_agents.yaml`
- [ ] `requirements.txt`
- [ ] `agents/` folder (all agent files)
- [ ] `src/pipeline/logger.py` (for logging)

## 🔧 Environment Variables Summary

**Required:**
```bash
AGENT_PREDICTION_API_URL=https://ai-health-agent-vuol.onrender.com/predict
```

**LLM (choose one):**
```bash
# Option 1: Together.ai
TOGETHER_API_KEY=your_key

# Option 2: OpenAI
OPENAI_API_KEY=sk-your_key

# Option 3: Ollama
AGENT_OLLAMA_BASE_URL=https://your-ollama-service.com
AGENT_OLLAMA_MODEL=phi3
AGENT_TEMPERATURE=0.1
```

## 📚 Documentation

- **Quick Start**: `RENDER_QUICK_START_AGENTS.md` (5 minutes)
- **Detailed Guide**: `RENDER_AGENTS_DEPLOYMENT.md` (full instructions)
- **Agent README**: `README_AGENTS.md` (complete documentation)

## 🐛 Common Issues

### Build Fails
- Check `requirements.txt` has all dependencies
- If using cloud LLM, install: `pip install langchain-together` or `langchain-openai`
- Check Render logs for specific errors

### Service Won't Start
- Verify environment variables are set correctly
- Check PORT is not hardcoded (Render sets it automatically)
- Check logs in Render dashboard

### LLM Connection Error
- Verify API key is correct
- Check API key has credits/quota
- Try a different LLM service

### Prediction API Timeout
- Prediction API may be sleeping (free tier)
- Use UptimeRobot to keep prediction API alive too
- Or upgrade to Starter plan

## ✅ Success Criteria

Your deployment is successful when:

- [ ] Health endpoint returns 200: `/agents/health`
- [ ] Full pipeline works: `/agents/run`
- [ ] All 4 agents execute successfully
- [ ] Returns operational plan JSON
- [ ] Service stays alive (with UptimeRobot)

## 🎯 Next Steps (After Deployment)

1. ✅ Test all endpoints
2. ✅ Document your API URL
3. ✅ Set up monitoring (UptimeRobot)
4. ✅ Test with real data
5. ⏭️ **Later**: Set up automation (we'll do this next!)

## 💡 Pro Tips

- **Start with Together.ai** - Easiest setup, very cheap
- **Use free tier** for testing, upgrade to Starter for production
- **Set up UptimeRobot** immediately to keep service alive
- **Monitor logs** in Render dashboard for any issues
- **Test locally first** before deploying

---

**Ready to deploy?** Follow `RENDER_QUICK_START_AGENTS.md` for the fastest path! 🚀

