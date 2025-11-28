# 🔧 Fix OpenAI Quota Error

## ❌ Error

```
Error code: 429 - You exceeded your current quota
```

**Meaning**: Your OpenAI API key has run out of credits.

---

## ✅ Solution Options

### Option 1: Add Credits to OpenAI (Recommended if you want best quality)

1. **Go to**: https://platform.openai.com
2. **Navigate**: Billing → Payment methods
3. **Add payment method** and add credits
4. **Cost**: ~$0.002 per request (very cheap)

**Keep using OpenAI** - just add credits.

---

### Option 2: Use Hugging Face (100% Free - No Credits Needed)

**Best for**: Free tier, no credit card needed

**Steps:**

1. **Get Hugging Face Token**:
   - Go to https://huggingface.co
   - Sign up (free)
   - Settings → Access Tokens → New Token
   - Copy token

2. **Add to Render**:
   - Render Dashboard → Your Service → Environment
   - **Remove** `OPENAI_API_KEY` (or leave it, Hugging Face takes priority)
   - **Add**:
     ```
     Key: HUGGINGFACE_API_KEY
     Value: your_hf_token_here
     ```

3. **Update requirements.txt** (if needed):
   ```bash
   # Already in requirements.txt, but verify:
   langchain-community>=0.2.0
   ```

4. **Redeploy**:
   - Render will auto-redeploy
   - Or manually trigger deploy

5. **Verify**:
   - Check logs: Should see "✅ Using Hugging Face Inference API for LLM (FREE)"
   - Health endpoint: Should show `"llm_provider": "huggingface"`

---

### Option 3: Use Different OpenAI Account

If you have another OpenAI account with credits:
1. Get new API key
2. Update `OPENAI_API_KEY` in Render
3. Redeploy

---

## 🎯 Quick Fix: Switch to Hugging Face

**Fastest solution** (5 minutes):

1. **Get HF token**: https://huggingface.co → Settings → Access Tokens
2. **Add to Render**: `HUGGINGFACE_API_KEY=your_token`
3. **Redeploy**
4. **Done!** ✅

**Free tier**: 1000 requests/day (plenty for testing)

---

## 📊 Comparison

| Service | Cost | Quality | Setup |
|---------|------|---------|-------|
| **OpenAI** | ~$0.002/req | ⭐⭐⭐⭐⭐ Excellent | Easy |
| **Hugging Face** | FREE | ⭐⭐⭐⭐ Good | Easy |
| **Together.ai** | Requires $5 | ⭐⭐⭐⭐ Good | Easy |

---

## 🔍 Verify After Switch

After switching to Hugging Face:

**Check logs:**
```
✅ Hugging Face API key detected
✅ Using Hugging Face Inference API for LLM (FREE)
```

**Check health:**
```bash
curl https://agents-ai-hfpb.onrender.com/agents/health
```

Should show:
```json
{
  "llm_provider": "huggingface",
  ...
}
```

---

## 💡 Recommendation

**For now**: Switch to Hugging Face (free, works immediately)

**For production**: Add credits to OpenAI (better quality, still very cheap)

---

**Quick action**: Get Hugging Face token and add to Render! 🚀

