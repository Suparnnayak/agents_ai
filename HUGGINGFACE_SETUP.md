# 🚀 Hugging Face Setup Guide

## Step-by-Step Instructions

### Step 1: Get Hugging Face API Key (FREE)

1. **Go to Hugging Face:**
   - Visit: https://huggingface.co/join
   - Sign up for a FREE account (or log in if you have one)

2. **Create API Token:**
   - Go to: https://huggingface.co/settings/tokens
   - Click **"New token"**
   - Name it: `hospital-agent-api` (or any name)
   - Select **"Read"** permission (that's enough)
   - Click **"Generate token"**

3. **Copy the Token:**
   - It will look like: `hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Copy it immediately** (you won't see it again!)

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
   - **Key:** `HUGGINGFACE_API_KEY`
   - **Value:** Paste your token (starts with `hf_`)
   - Click **"Save Changes"**

5. **Redeploy:**
   - Render will automatically redeploy (or click "Manual Deploy" → "Deploy latest commit")
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
  "llm_provider": "huggingface",
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

Your agents will now use Hugging Face (completely FREE) instead of Gemini!

---

## 🐛 Troubleshooting

### "Hugging Face API key not detected"
- Make sure the key name is exactly: `HUGGINGFACE_API_KEY` (all caps)
- Make sure you saved and redeployed

### "Model not found"
- The code uses `meta-llama/Llama-3-8b-chat-hf` by default
- This model is FREE and should work immediately

### Still having issues?
- Check Render logs: Render Dashboard → Your Service → Logs
- Look for "✅ Using Hugging Face Inference API for LLM (FREE)"

---

## 💡 Benefits of Hugging Face

- ✅ **100% FREE** - No credit limits
- ✅ **No setup issues** - Works immediately
- ✅ **Good quality** - Uses Llama 3 model
- ✅ **Reliable** - No model name errors

---

**Need help? Check Render logs for error messages!**

