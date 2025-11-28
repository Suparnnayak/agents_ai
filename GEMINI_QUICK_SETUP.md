# 🚀 Quick Setup: Switch to Google Gemini

## ✅ What I've Done

1. ✅ Added Gemini support to `agents/llm_client.py`
2. ✅ Updated health endpoint to show Gemini
3. ✅ Added `langchain-google-genai` to requirements.txt
4. ✅ Gemini now has **highest priority** (checked first)

---

## 🎯 3-Step Setup

### Step 1: Get Gemini API Key (2 min)

1. **Go to**: https://aistudio.google.com/app/apikey
2. **Sign in** with Google account
3. **Click**: "Create API Key"
4. **Copy the key** (starts with `AIza...`)

---

### Step 2: Add to Render (1 min)

1. **Render Dashboard** → Your Service → Environment
2. **Add**:
   ```
   Key: GOOGLE_API_KEY
   Value: AIza_your_key_here
   ```
3. **Save**

---

### Step 3: Push Code & Redeploy (2 min)

```bash
# Add updated files
git add agents/llm_client.py agent_api_server.py requirements.txt
git commit -m "Add Google Gemini support"
git push
```

Render will auto-deploy (or manually trigger).

---

## ✅ Verify

After redeploy, check logs:
```
✅ Google Gemini API key detected
✅ Using Google Gemini for LLM
```

Health endpoint:
```bash
curl https://agents-ai-hfpb.onrender.com/agents/health
```

Should show:
```json
{
  "llm_provider": "gemini",
  ...
}
```

---

## 🧪 Test

```bash
curl -X POST https://agents-ai-hfpb.onrender.com/agents/run \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```

**Should work now!** ✅

---

## 💡 Why Gemini?

- ✅ **Free tier** (60 requests/minute)
- ✅ **Good quality** (comparable to GPT-3.5)
- ✅ **Fast responses**
- ✅ **No credit card** needed for free tier

---

**That's it!** Get your Gemini key and add it to Render! 🚀

