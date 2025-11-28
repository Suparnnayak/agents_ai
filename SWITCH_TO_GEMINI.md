# 🔄 Switch to Google Gemini - Setup Guide

## ✅ Why Gemini?

- ✅ **Free tier available** (generous limits)
- ✅ **Good quality** output
- ✅ **Fast responses**
- ✅ **Easy setup**

---

## 🚀 Quick Setup (5 Minutes)

### Step 1: Get Gemini API Key

1. **Go to**: https://aistudio.google.com/app/apikey
2. **Sign in** with your Google account
3. **Click**: "Create API Key"
4. **Select**: Create API key in new project (or existing project)
5. **Copy the API key** - you'll need it in Step 2

**Note**: Gemini has a free tier with generous limits!

---

### Step 2: Add to Render

1. **Go to**: https://dashboard.render.com
2. **Click**: Your service (`hospital-agent-api` or `agents-ai-hfpb`)
3. **Click**: "Environment" tab
4. **Add environment variable**:
   ```
   Key: GOOGLE_API_KEY
   Value: your_gemini_api_key_here
   ```
   (Paste the key you copied in Step 1)

5. **Optional**: Remove or keep `OPENAI_API_KEY` (Gemini takes priority if both are set)

6. **Click**: "Save Changes"

---

### Step 3: Update Build Command (Important!)

Since we need to install `langchain-google-genai`, update the build command:

**In Render Dashboard → Your Service → Settings:**

**Build Command:**
```bash
pip install -r requirements.txt && pip install langchain-google-genai
```

**Or add to requirements.txt** (recommended):
```bash
langchain-google-genai>=1.0.0
```

Then push to GitHub:
```bash
git add requirements.txt
git commit -m "Add Gemini support"
git push
```

---

### Step 4: Redeploy

Render will **auto-redeploy** after:
- Setting environment variable
- Pushing updated code

**Or manually trigger**:
- Render Dashboard → Your Service → Manual Deploy

---

### Step 5: Verify

After redeploy, check logs. You should see:
```
✅ Google Gemini API key detected (length: 39)
✅ Using Google Gemini for LLM
```

**Check health endpoint:**
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

## 🧪 Test After Switch

```bash
curl -X POST https://agents-ai-hfpb.onrender.com/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "data": [{
      "date": "2025-12-05",
      "admissions": 210,
      "aqi": 240,
      "temp": 26.0,
      "humidity": 70,
      "rainfall": 5.0,
      "wind_speed": 9.0,
      "mobility_index": 65,
      "outbreak_index": 45,
      "festival_flag": 1,
      "holiday_flag": 0,
      "weekday": 5,
      "is_weekend": 1,
      "population_density": 15000,
      "hospital_beds": 650,
      "staff_count": 280,
      "city_id": 2,
      "hospital_id_enc": 222
    }],
    "hospital_id": "HOSP-123",
    "disease_sensitivity": 0.5,
    "mode": "ensemble"
  }'
```

**Should now work!** ✅

---

## 📊 Gemini Free Tier

- ✅ **Generous free tier** (60 requests/minute)
- ✅ **Good quality** output
- ✅ **Fast responses**
- ✅ **No credit card** required for free tier

---

## 🔄 Priority Order

Your code now checks LLMs in this order:
1. **Gemini** (if `GOOGLE_API_KEY` is set)
2. **OpenAI** (if `OPENAI_API_KEY` is set)
3. **Hugging Face** (if `HUGGINGFACE_API_KEY` is set)
4. **Together.ai** (if `TOGETHER_API_KEY` is set)
5. **Ollama** (fallback)

---

## 📝 Quick Checklist

- [ ] Get Gemini API key from https://aistudio.google.com/app/apikey
- [ ] Add `GOOGLE_API_KEY` to Render environment variables
- [ ] Add `langchain-google-genai>=1.0.0` to requirements.txt
- [ ] Push updated code to GitHub
- [ ] Wait for redeploy (2-3 minutes)
- [ ] Verify logs show "✅ Using Google Gemini for LLM"
- [ ] Test API endpoint

---

## 🐛 Troubleshooting

### Build Fails - Missing Package

**Error**: `ModuleNotFoundError: No module named 'langchain_google_genai'`

**Solution**: 
- Add to build command: `pip install -r requirements.txt && pip install langchain-google-genai`
- Or add to requirements.txt and push

### API Key Not Detected

**Check**:
- Key is set correctly in Render
- No extra spaces
- Key starts with `AIza...` (Gemini keys start with this)

### Still Using OpenAI

**Check**:
- `GOOGLE_API_KEY` is set (Gemini takes priority)
- Service has been redeployed
- Logs show which key is detected

---

## ✅ Summary

**Action**: 
1. Get Gemini API key (2 min)
2. Add `GOOGLE_API_KEY` to Render (1 min)
3. Add `langchain-google-genai` to requirements.txt (1 min)
4. Push and redeploy (2-3 min)
5. Test! ✅

**Total time**: ~5 minutes

---

**Ready?** Get your Gemini API key and add it to Render! 🚀

