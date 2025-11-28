# 🔍 Verify OpenAI Setup - Your Service is Live!

## ✅ Good News

Your service is **live and healthy** at: https://agents-ai-hfpb.onrender.com/agents/health

## ⚠️ Issue Found

The health check shows:
```json
{
  "ollama_model": "phi3",
  "ollama_url": "http://localhost:11434"
}
```

This means **OpenAI is NOT being detected** - it's falling back to Ollama.

---

## 🔧 Fix: Set OpenAI API Key in Render

### Step 1: Go to Render Dashboard

1. **Go to**: https://dashboard.render.com
2. **Click**: Your service `hospital-agent-api` (or `agents-ai-hfpb`)
3. **Click**: "Environment" tab (left sidebar)

### Step 2: Add/Verify Environment Variable

**Check if `OPENAI_API_KEY` exists:**

- If **NOT there**: Click "Add Environment Variable"
- If **already there**: Click to edit it

**Set:**
```
Key: OPENAI_API_KEY
Value: sk-your_openai_key_here
```

**Important:**
- ✅ Key must start with `sk-`
- ✅ No spaces before/after
- ✅ Copy the full key from OpenAI dashboard

### Step 3: Save and Redeploy

1. **Click**: "Save Changes"
2. **Render will auto-redeploy** (or click "Manual Deploy")
3. **Wait**: 2-3 minutes for redeploy

### Step 4: Check Logs

After redeploy, check logs. You should see:
```
✅ OpenAI API key detected (length: 51)
✅ Using OpenAI for LLM
```

---

## 🧪 Test After Fix

### Test Health Endpoint

```bash
curl https://agents-ai-hfpb.onrender.com/agents/health
```

**Expected (after fix):**
```json
{
  "status": "healthy",
  "service": "hospital-agent-api",
  "ollama_url": "http://localhost:11434",
  "ollama_model": "phi3",
  "prediction_api": "https://ai-health-agent-vuol.onrender.com/predict"
}
```

**Note**: The health endpoint still shows Ollama config (that's just default values), but the **actual LLM being used** will be OpenAI (check logs).

### Test Full Pipeline

```bash
curl -X POST https://agents-ai-hfpb.onrender.com/agents/run \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```

**If OpenAI is working**, you'll get a proper response with operational plan.

**If still using Ollama**, you'll get an error (Ollama not available on Render).

---

## 🔍 How to Verify OpenAI is Working

### Method 1: Check Logs

In Render Dashboard → Logs, look for:
```
✅ OpenAI API key detected (length: 51)
✅ Using OpenAI for LLM
```

**NOT:**
```
⚠️  langchain-together not installed, falling back to Ollama
✅ Using Ollama (phi3) for LLM
```

### Method 2: Test API Call

Make a test request to `/agents/run`. If it works without errors, OpenAI is being used.

If you get connection errors to `localhost:11434`, it's still trying to use Ollama.

---

## 📝 Quick Checklist

- [ ] `OPENAI_API_KEY` is set in Render environment variables
- [ ] Key starts with `sk-` and has no extra spaces
- [ ] Service has been redeployed after setting the variable
- [ ] Logs show "✅ Using OpenAI for LLM"
- [ ] Test request to `/agents/run` works

---

## 🐛 If Still Not Working

### Check 1: Environment Variable Format

**Wrong:**
```
OPENAI_API_KEY = sk-...  (has spaces)
OPENAI_API_KEY= sk-...   (space after =)
```

**Correct:**
```
OPENAI_API_KEY=sk-...     (no spaces)
```

### Check 2: Key is Valid

1. Go to https://platform.openai.com
2. API Keys → Check your key is active
3. Copy it again (make sure it's complete)

### Check 3: Code is Updated

Make sure you've pushed the updated `agents/llm_client.py`:
```bash
git status
git log --oneline -5  # Check recent commits
```

### Check 4: Redeploy

After setting environment variable, **manually trigger redeploy**:
- Render Dashboard → Your Service → Manual Deploy

---

## ✅ Success Indicators

After fixing, you should see:

1. **Logs show**:
   ```
   ✅ OpenAI API key detected
   ✅ Using OpenAI for LLM
   ```

2. **API calls work**:
   ```bash
   curl -X POST https://agents-ai-hfpb.onrender.com/agents/run ...
   # Returns operational plan (no errors)
   ```

3. **No Ollama connection errors** in logs

---

**Action Required**: Go to Render Dashboard → Environment → Add/Edit `OPENAI_API_KEY` → Redeploy

Your service is live, just need to set the OpenAI key! 🚀

