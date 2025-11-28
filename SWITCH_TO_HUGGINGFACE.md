# 🔄 Switch to Hugging Face (Free LLM) - Quick Fix

## ❌ Current Error

```
Error code: 429 - You exceeded your current quota
```

**Your OpenAI credits are exhausted.**

---

## ✅ Quick Fix: Use Hugging Face (100% Free)

### Step 1: Get Hugging Face Token (2 minutes)

1. **Go to**: https://huggingface.co
2. **Sign up** (free account, no credit card needed)
3. **Navigate**: Settings → Access Tokens
4. **Click**: "New token"
5. **Name it**: "Hospital Agent API" (optional)
6. **Select**: "Read" permission (sufficient)
7. **Click**: "Generate token"
8. **Copy the token** - you'll need it in Step 2

---

### Step 2: Add to Render (1 minute)

1. **Go to**: https://dashboard.render.com
2. **Click**: Your service (`hospital-agent-api` or `agents-ai-hfpb`)
3. **Click**: "Environment" tab
4. **Add new variable**:
   ```
   Key: HUGGINGFACE_API_KEY
   Value: hf_your_token_here
   ```
   (Paste the token you copied in Step 1)

5. **Optional**: You can remove `OPENAI_API_KEY` or leave it (Hugging Face takes priority if both are set)

6. **Click**: "Save Changes"

---

### Step 3: Redeploy (Automatic)

Render will **auto-redeploy** after saving environment variables (takes 2-3 minutes).

**Or manually trigger**:
- Render Dashboard → Your Service → Manual Deploy

---

### Step 4: Verify

After redeploy, check logs. You should see:
```
✅ Hugging Face API key detected
✅ Using Hugging Face Inference API for LLM (FREE)
```

**Check health endpoint:**
```bash
curl https://agents-ai-hfpb.onrender.com/agents/health
```

Should show:
```json
{
  "llm_provider": "huggingface",
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

## 📊 Hugging Face Free Tier

- ✅ **1000 requests/day** (plenty for testing)
- ✅ **No credit card** required
- ✅ **Good quality** output
- ✅ **Free forever**

---

## 🔄 Switch Back to OpenAI Later

If you add credits to OpenAI later:

1. **Add credits** to OpenAI account
2. **Keep both keys** in Render (OpenAI takes priority)
3. **Or remove** `HUGGINGFACE_API_KEY` to use OpenAI only

---

## ✅ Summary

**Action**: 
1. Get Hugging Face token (2 min)
2. Add `HUGGINGFACE_API_KEY` to Render (1 min)
3. Wait for redeploy (2-3 min)
4. Test! ✅

**Total time**: ~5 minutes

---

**Ready?** Get your Hugging Face token and add it to Render! 🚀

