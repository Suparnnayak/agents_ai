# 🔑 Set OpenAI API Key in Render - Quick Guide

## 🎯 Your Service Status

✅ **Service is LIVE**: https://agents-ai-hfpb.onrender.com/agents/health  
⚠️ **Issue**: OpenAI key not set - currently using Ollama (which won't work on Render)

---

## 🚀 Quick Fix (2 Minutes)

### Step 1: Go to Render Dashboard

1. **Open**: https://dashboard.render.com
2. **Click**: Your service (probably named `hospital-agent-api` or `agents-ai-hfpb`)
3. **Click**: "Environment" tab (left sidebar)

### Step 2: Add OpenAI API Key

1. **Click**: "Add Environment Variable" (or find `OPENAI_API_KEY` if it exists)
2. **Set**:
   ```
   Key: OPENAI_API_KEY
   Value: sk-your_openai_key_here
   ```
3. **Important**:
   - ✅ Key must start with `sk-`
   - ✅ No spaces before or after
   - ✅ Copy the complete key from OpenAI dashboard

### Step 3: Save and Wait

1. **Click**: "Save Changes"
2. **Render will auto-redeploy** (takes 2-3 minutes)
3. **Or manually**: Click "Manual Deploy" button

### Step 4: Verify

After redeploy, check health endpoint:
```bash
curl https://agents-ai-hfpb.onrender.com/agents/health
```

**Should now show:**
```json
{
  "status": "healthy",
  "llm_provider": "openai",  ← This confirms OpenAI is being used!
  ...
}
```

**Check logs** in Render Dashboard → Logs:
```
✅ OpenAI API key detected (length: 51)
✅ Using OpenAI for LLM
```

---

## 📝 Where to Get OpenAI Key

1. **Go to**: https://platform.openai.com
2. **Sign in** (or sign up - get $5 free credit!)
3. **Navigate**: API Keys (left sidebar)
4. **Click**: "Create new secret key"
5. **Copy** the key (starts with `sk-`)
6. **Paste** into Render environment variable

---

## ✅ Verification Checklist

After setting the key:

- [ ] `OPENAI_API_KEY` is set in Render environment variables
- [ ] Key starts with `sk-` and has no spaces
- [ ] Service has been redeployed
- [ ] Health endpoint shows `"llm_provider": "openai"`
- [ ] Logs show "✅ Using OpenAI for LLM"
- [ ] Test request to `/agents/run` works

---

## 🧪 Test After Setting Key

```bash
# Test health (should show llm_provider: "openai")
curl https://agents-ai-hfpb.onrender.com/agents/health

# Test full pipeline
curl -X POST https://agents-ai-hfpb.onrender.com/agents/run \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```

---

## 🐛 Troubleshooting

### Still Shows "ollama" in health check?

1. **Check**: Environment variable is saved correctly
2. **Check**: No typos in variable name (`OPENAI_API_KEY` not `OPENAI_KEY`)
3. **Check**: Service has been redeployed after setting variable
4. **Check**: Logs show "OpenAI API key detected"

### Getting Errors?

- **"Invalid API key"**: Check key is correct, no extra spaces
- **"Insufficient quota"**: Check OpenAI dashboard for credit balance
- **Connection errors**: Make sure service is redeployed

---

**That's it!** Just set the `OPENAI_API_KEY` environment variable in Render and redeploy. 🚀

