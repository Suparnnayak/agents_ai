# 🎯 Next Steps - Deploy Agents on Render

## Step-by-Step Action Plan

### Step 1: Get Cloud LLM API Key (2 minutes) ⭐

**Recommended: OpenAI (Easiest & $5 Free Credit)**

1. **Go to**: https://platform.openai.com
2. **Sign up** (get $5 free credit!)
3. **Get API key**: API Keys → Create new key
4. **Copy the key** - you'll need it in Step 4

**Alternative: Hugging Face (100% Free)**
- Go to https://huggingface.co
- Sign up
- Settings → Access Tokens → New Token
- Copy token

**See `FREE_LLM_OPTIONS.md` for all free options!**

---

### Step 2: Push Code to GitHub (1 minute)

Make sure your code is pushed to GitHub:

```bash
# Check what needs to be committed
git status

# Add all files
git add .

# Commit
git commit -m "Ready for Render deployment - Agent API"

# Push to GitHub
git push origin main
```

**Verify**: Go to your GitHub repo and check these files exist:
- ✅ `agent_api_server.py`
- ✅ `render_agents.yaml`
- ✅ `requirements.txt`
- ✅ `agents/` folder

---

### Step 3: Deploy on Render (3 minutes)

1. **Go to Render Dashboard**: https://dashboard.render.com
   - Sign up if you don't have an account (free)

2. **Create New Web Service**:
   - Click **"New +"** button (top right)
   - Select **"Web Service"**

3. **Connect GitHub**:
   - Click **"Connect GitHub"** (if first time, authorize Render)
   - Select your repository
   - Click **"Connect"**

4. **Render Auto-Detection**:
   - Render should auto-detect `render_agents.yaml` ✅
   - If not, manually set:
     - **Name**: `hospital-agent-api`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python agent_api_server.py`

5. **Set Environment Variables**:
   - Scroll to **"Environment"** section
   - Click **"Add Environment Variable"**
   - Add these:

   ```bash
   # Required
   AGENT_PREDICTION_API_URL = https://ai-health-agent-vuol.onrender.com/predict
   
   # LLM (choose one - recommended: OpenAI)
   OPENAI_API_KEY = sk-your_openai_key_here
   # OR
   # HUGGINGFACE_API_KEY = your_hf_token_here
   ```

6. **Choose Plan**:
   - **Free** (for testing) - spins down after inactivity
   - **Starter ($7/month)** - always running (recommended for production)

7. **Deploy**:
   - Click **"Create Web Service"**
   - Wait 2-5 minutes for build
   - Watch the logs to see progress

---

### Step 4: Test Your Deployment (1 minute)

Once deployed, you'll get a URL like: `https://hospital-agent-api.onrender.com`

**Test Health Endpoint:**
```bash
curl https://your-app.onrender.com/agents/health
```

**Expected Response:**
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
curl -X POST https://your-app.onrender.com/agents/run \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```

---

### Step 5: Keep Service Alive (2 minutes) ⚠️

**Important for Free Tier**: Set up UptimeRobot to keep service alive

1. **Go to**: https://uptimerobot.com
2. **Sign up** (free)
3. **Add New Monitor**:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: Hospital Agent API
   - **URL**: `https://your-app.onrender.com/agents/health`
   - **Monitoring Interval**: 5 minutes
4. **Create Monitor**
5. **Done!** ✅ Service will stay alive

---

## ✅ Checklist

Before you start:
- [ ] Together.ai account created (or OpenAI)
- [ ] API key copied
- [ ] Code pushed to GitHub
- [ ] Render account created

During deployment:
- [ ] Web service created on Render
- [ ] GitHub repo connected
- [ ] Environment variables set
- [ ] Service deployed successfully

After deployment:
- [ ] Health endpoint works
- [ ] Full pipeline test passes
- [ ] UptimeRobot monitor set up
- [ ] API URL saved/documentation

---

## 🐛 If Something Goes Wrong

### Build Fails
- **Check**: Render logs for specific error
- **Common fix**: Make sure `requirements.txt` has all dependencies
- **If using cloud LLM**: Add to requirements.txt:
  ```bash
  langchain-together>=0.1.0  # For Together.ai
  # OR
  langchain-openai>=0.1.0    # For OpenAI
  ```

### Service Won't Start
- **Check**: Environment variables are set correctly
- **Check**: Logs in Render dashboard
- **Verify**: API keys are valid

### LLM Connection Error
- **Check**: API key is correct (no extra spaces)
- **Check**: API key has credits/quota
- **Try**: Different LLM service

### Prediction API Timeout
- **Solution**: Use UptimeRobot to keep prediction API alive too
- **Or**: Upgrade prediction API to Starter plan

---

## 📞 Need Help?

1. **Check Render Logs**: Dashboard → Your Service → Logs tab
2. **Test Locally First**: `python agent_api_server.py`
3. **Check Documentation**: `RENDER_QUICK_START_AGENTS.md`

---

## 🎯 What's Next After Deployment?

Once your agent API is live:

1. ✅ **Test all endpoints**
2. ✅ **Document your API URL**
3. ✅ **Set up monitoring** (UptimeRobot)
4. ⏭️ **Set up automation** (we'll do this next!)

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

**Ready?** Start with Step 1 - Get your Together.ai API key! 🎉

