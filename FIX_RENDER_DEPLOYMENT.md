# 🔧 Fix Render Deployment Issues

## Issues Found in Your Logs

1. ⚠️ **Not using OpenAI** - Falling back to Ollama
2. ⚠️ **Using Flask dev server** - Should use Gunicorn for production
3. ⚠️ **Ollama deprecation warning** - Not critical

## ✅ Fixes Applied

### 1. Fixed OpenAI Detection

**Problem**: OpenAI API key not being detected properly

**Fix**: Updated `agents/llm_client.py` to:
- Better detect `OPENAI_API_KEY` environment variable
- Add debug logging to show which LLM is being used
- Check for empty strings

### 2. Added Gunicorn for Production

**Problem**: Using Flask dev server (not production-ready)

**Fix**: 
- Added `gunicorn>=21.2.0` to `requirements.txt`
- Created `Procfile` with Gunicorn command
- Updated `render_agents.yaml` start command

### 3. Updated Start Command

**Old**: `python agent_api_server.py`
**New**: `gunicorn agent_api_server:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

---

## 🚀 What to Do Now

### Step 1: Verify Environment Variables

In Render Dashboard → Your Service → Environment:

**Check these are set:**
```
AGENT_PREDICTION_API_URL=https://ai-health-agent-vuol.onrender.com/predict
OPENAI_API_KEY=sk-your_key_here
```

**Important**: 
- Make sure `OPENAI_API_KEY` is set correctly
- No extra spaces
- Key starts with `sk-`

### Step 2: Push Updated Code

```bash
git add .
git commit -m "Add Gunicorn and fix OpenAI detection"
git push
```

### Step 3: Redeploy

Render will auto-deploy, or manually trigger:
- Render Dashboard → Your Service → Manual Deploy

### Step 4: Check Logs

After redeploy, check logs. You should see:
```
✅ OpenAI API key detected (length: 51)
✅ Using OpenAI for LLM
```

Instead of:
```
⚠️  langchain-together not installed, falling back to Ollama
```

---

## 📝 Updated Files

1. ✅ `requirements.txt` - Added Gunicorn
2. ✅ `Procfile` - Added Gunicorn start command
3. ✅ `render_agents.yaml` - Updated start command
4. ✅ `agents/llm_client.py` - Fixed OpenAI detection
5. ✅ `agent_api_server.py` - Production mode detection

---

## 🔍 Verify Deployment

After redeploy, check:

1. **Logs show OpenAI**:
   ```
   ✅ OpenAI API key detected
   ✅ Using OpenAI for LLM
   ```

2. **No dev server warning**:
   ```
   ✅ Using Gunicorn (production server)
   ```

3. **Test API**:
   ```bash
   curl https://agents-ai-hfpb.onrender.com/agents/health
   ```

4. **Test Full Pipeline**:
   ```bash
   curl -X POST https://agents-ai-hfpb.onrender.com/agents/run \
     -H "Content-Type: application/json" \
     -d @samples/sample_request.json
   ```

---

## 🐛 If Still Not Working

### OpenAI Still Not Detected

1. **Check environment variable**:
   - Render Dashboard → Environment
   - Verify `OPENAI_API_KEY` is set
   - Check for typos

2. **Check logs**:
   - Look for "OpenAI API key detected" message
   - If not showing, key might not be set

3. **Test locally**:
   ```bash
   export OPENAI_API_KEY=sk-your_key
   python -c "from agents.llm_client import llm_client; print(llm_client)"
   ```

### Gunicorn Not Starting

1. **Check Procfile exists** in repo
2. **Check start command** in Render settings
3. **Check Gunicorn installed**: Look for "Successfully installed gunicorn" in build logs

---

## ✅ Success Indicators

After fixes, you should see:

✅ Build logs:
```
Successfully installed gunicorn-21.2.0
```

✅ Runtime logs:
```
✅ OpenAI API key detected (length: 51)
✅ Using OpenAI for LLM
[INFO] Starting gunicorn 21.2.0
[INFO] Listening at: http://0.0.0.0:10000
```

✅ Health check:
```json
{
  "status": "healthy",
  "service": "hospital-agent-api"
}
```

---

**Push the updated code and redeploy!** 🚀

