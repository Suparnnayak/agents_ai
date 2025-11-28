# ✅ Gemini Support Added - Setup Instructions

## 🎉 What's Done

✅ **Gemini support added** to `agents/llm_client.py`
✅ **Health endpoint updated** to show Gemini provider
✅ **Requirements updated** with `langchain-google-genai`
✅ **Gemini has highest priority** (checked before OpenAI)

---

## 🚀 Quick Setup (3 Steps)

### Step 1: Get Gemini API Key

1. **Go to**: https://aistudio.google.com/app/apikey
2. **Sign in** with Google account
3. **Click**: "Create API Key"
4. **Copy the key** (starts with `AIza...`)

**Free tier**: 60 requests/minute, generous limits!

---

### Step 2: Add to Render

1. **Render Dashboard** → Your Service → Environment
2. **Add**:
   ```
   Key: GOOGLE_API_KEY
   Value: AIza_your_key_here
   ```
3. **Save Changes**

**Optional**: Remove `OPENAI_API_KEY` (or keep it - Gemini takes priority)

---

### Step 3: Push Code & Redeploy

```bash
# Push updated code
git add agents/llm_client.py agent_api_server.py requirements.txt
git commit -m "Add Google Gemini support"
git push
```

Render will auto-deploy (2-3 minutes).

---

## ✅ Verify

After redeploy:

**Check logs:**
```
✅ Google Gemini API key detected (length: 39)
✅ Using Google Gemini for LLM
```

**Check health:**
```bash
curl https://agents-ai-hfpb.onrender.com/agents/health
```

Should show:
```json
{
  "llm_provider": "gemini",
  "status": "healthy",
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

**Should work perfectly!** ✅

---

## 📊 LLM Priority Order

Your code now checks in this order:
1. **Gemini** (if `GOOGLE_API_KEY` set) ← Highest priority
2. **OpenAI** (if `OPENAI_API_KEY` set)
3. **Hugging Face** (if `HUGGINGFACE_API_KEY` set)
4. **Together.ai** (if `TOGETHER_API_KEY` set)
5. **Ollama** (fallback)

---

## 💡 Why Gemini?

- ✅ **Free tier** (60 requests/minute)
- ✅ **Good quality** (comparable to GPT-3.5)
- ✅ **Fast responses**
- ✅ **No credit card** needed for free tier
- ✅ **Reliable** (Google infrastructure)

---

## 📝 Files Updated

- ✅ `agents/llm_client.py` - Added Gemini support
- ✅ `agent_api_server.py` - Updated health endpoint
- ✅ `requirements.txt` - Added `langchain-google-genai`

---

**Ready!** Get your Gemini API key and add it to Render! 🚀

