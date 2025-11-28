# 🚀 Groq Setup Guide - FAST & FREE!

## Why Groq? ⚡

**Groq is EXCELLENT for your use case:**
- ✅ **SUPER FAST** - Uses LPUs (Language Processing Units) - fastest inference
- ✅ **FREE TIER** - Generous free tier (14,400 requests/day)
- ✅ **RELIABLE** - No model name issues, stable API
- ✅ **EASY SETUP** - Just one API key
- ✅ **Great Models** - Llama 3.1 70B, Mixtral, and more

**Perfect for production!** 🎯

---

## Step-by-Step Setup

### Step 1: Get Groq API Key (FREE)

1. **Go to Groq:**
   - Visit: https://console.groq.com
   - Sign up for a FREE account (or log in)

2. **Create API Key:**
   - Go to: https://console.groq.com/keys
   - Click **"Create API Key"**
   - Name it: `hospital-agent-api` (or any name)
   - Click **"Submit"**

3. **Copy the Key:**
   - It will look like: `gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Copy it immediately!**

---

### Step 2: Set API Key in Render

1. **Go to Render Dashboard:**
   - Visit: https://dashboard.render.com
   - Log in

2. **Find Your Agent Service:**
   - Click on your agent service (e.g., `agents-ai-hfpb`)

3. **Go to Environment Tab:**
   - Click **"Environment"** in the left sidebar

4. **Add New Environment Variable:**
   - Click **"Add Environment Variable"**
   - **Key:** `GROQ_API_KEY`
   - **Value:** Paste your key (starts with `gsk_`)
   - Click **"Save Changes"**

5. **Redeploy:**
   - Render will automatically redeploy (or click "Manual Deploy")
   - Wait 2-3 minutes for deployment

---

### Step 3: Verify It Works

**Test the API:**
```bash
curl https://agents-ai-hfpb.onrender.com/agents/health
```

**Expected Response:**
```json
{
  "llm_provider": "groq",
  "status": "healthy",
  ...
}
```

**Test Full Pipeline:**
```bash
curl -X POST "https://agents-ai-hfpb.onrender.com/agents/run" \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```

---

## ✅ That's It!

Your agents will now use Groq - the **FASTEST** and **FREE** option! ⚡

---

## 🎯 Groq Models Available

The code uses `llama-3.1-70b-versatile` by default, but you can change it:

**Available Models:**
- `llama-3.1-70b-versatile` (default - best quality)
- `llama-3.1-8b-instant` (faster, smaller)
- `mixtral-8x7b-32768` (great for long context)
- `gemma-7b-it` (Google's model)

**To change model:** Edit `agents/llm_client.py` line with `model="llama-3.1-70b-versatile"`

---

## 💰 Free Tier Limits

- **14,400 requests/day** (FREE)
- **30 requests/minute** (rate limit)
- **No credit card required**

**More than enough for your hospital agent system!** ✅

---

## 🐛 Troubleshooting

### "Groq API key not detected"
- Make sure the key name is exactly: `GROQ_API_KEY` (all caps)
- Make sure you saved and redeployed

### "Rate limit exceeded"
- Free tier: 30 requests/minute
- If you hit this, wait 1 minute and try again
- Or upgrade to paid tier for higher limits

### Still having issues?
- Check Render logs: Render Dashboard → Your Service → Logs
- Look for "✅ Using Groq for LLM (FAST & FREE)"

---

## 🚀 Why Groq is Better

| Feature | Groq | Hugging Face | Gemini |
|---------|------|--------------|--------|
| Speed | ⚡⚡⚡ FASTEST | 🐌 Slow | 🐌 Slow |
| Free Tier | ✅ 14,400/day | ✅ Unlimited | ✅ Limited |
| Reliability | ✅ Excellent | ⚠️ Variable | ⚠️ Model issues |
| Setup | ✅ Easy | ✅ Easy | ⚠️ Complex |

**Groq wins!** 🏆

---

## 📝 Code Already Updated

The code now:
- ✅ Supports Groq (highest priority)
- ✅ Falls back to other providers if Groq fails
- ✅ Uses `llama-3.1-70b-versatile` (best quality)
- ✅ Auto-detects in health endpoint

**Just set `GROQ_API_KEY` and deploy!** 🚀

---

**Need help? Check Render logs for error messages!**

