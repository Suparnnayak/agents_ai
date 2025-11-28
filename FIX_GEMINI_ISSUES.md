# 🔧 Fix Gemini Issues - Troubleshooting Guide

## Common Issues and Fixes

### Issue 1: Import Error

**Error**: `ModuleNotFoundError: No module named 'langchain_google_genai'`

**Fix**:
1. **Update build command** in Render:
   ```
   pip install -r requirements.txt && pip install langchain-google-genai
   ```

2. **Or add to requirements.txt**:
   ```bash
   langchain-google-genai>=1.0.0
   ```

3. **Push and redeploy**

---

### Issue 2: Response Format Error

**Error**: `AttributeError: 'AIMessage' object has no attribute 'content'` or similar

**Fix**: ✅ **Already fixed!** The code now handles different response formats:
- Gemini returns `AIMessage` with `.content` attribute
- OpenAI returns string directly
- Code handles both automatically

---

### Issue 3: API Key Not Detected

**Error**: Still using Ollama instead of Gemini

**Check**:
1. **Environment variable name**: Must be `GOOGLE_API_KEY` (not `GEMINI_API_KEY`)
2. **Value**: Should start with `AIza...`
3. **No spaces**: Check for extra spaces before/after
4. **Redeploy**: Service must be redeployed after setting variable

**Verify in logs**:
```
✅ Google Gemini API key detected (length: 39)
✅ Using Google Gemini for LLM
```

---

### Issue 4: JSON Parsing Error

**Error**: `OutputParserException: Failed to parse JSON`

**Fix**: ✅ **Already improved!** The code now:
- Handles different response formats
- Better JSON extraction
- Improved error messages

**If still failing**:
- Check prompts in agent files
- Try a different model: `gemini-pro` instead of `gemini-1.5-flash`

---

### Issue 5: Rate Limit / Quota Error

**Error**: `429 RESOURCE_EXHAUSTED` or quota exceeded

**Fix**:
1. **Check quota**: https://aistudio.google.com/app/apikey
2. **Free tier limits**: 60 requests/minute
3. **Wait**: Rate limits reset quickly
4. **Upgrade**: If needed, add billing to Google Cloud

---

### Issue 6: Model Not Found

**Error**: `Model not found: gemini-1.5-flash`

**Fix**: Try different model names:
- `gemini-pro`
- `gemini-1.5-pro`
- `gemini-1.5-flash-latest`

Update in `agents/llm_client.py`:
```python
model="gemini-pro",  # Instead of gemini-1.5-flash
```

---

## 🔍 Debug Steps

### Step 1: Check Logs

In Render Dashboard → Logs, look for:
```
✅ Google Gemini API key detected
✅ Using Google Gemini for LLM
```

**If you see**:
```
⚠️  Gemini setup failed: ...
```
→ Check the error message for details

### Step 2: Test Health Endpoint

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

### Step 3: Test Simple Request

```bash
curl -X POST https://agents-ai-hfpb.onrender.com/agents/monitor \
  -H "Content-Type: application/json" \
  -d '{
    "aqi": 240,
    "festival_score": 1.0,
    "weather_risk": 0.3,
    "disease_sensitivity": 0.5
  }'
```

**If this works**, the issue is with full pipeline.
**If this fails**, the issue is with Gemini setup.

---

## ✅ What I've Fixed

1. ✅ **Response format handling** - Now handles Gemini's `AIMessage` format
2. ✅ **Better error messages** - Shows what went wrong
3. ✅ **Improved JSON extraction** - Better parsing of LLM output
4. ✅ **Error handling** - More robust exception handling

---

## 🧪 Test After Fixes

```bash
# Test health
curl https://agents-ai-hfpb.onrender.com/agents/health

# Test monitor agent (simplest)
curl -X POST https://agents-ai-hfpb.onrender.com/agents/monitor \
  -H "Content-Type: application/json" \
  -d '{"aqi": 240, "festival_score": 1.0, "weather_risk": 0.3, "disease_sensitivity": 0.5}'

# Test full pipeline
curl -X POST https://agents-ai-hfpb.onrender.com/agents/run \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```

---

## 📝 Quick Checklist

- [ ] `GOOGLE_API_KEY` is set in Render (not `GEMINI_API_KEY`)
- [ ] Key starts with `AIza...` and has no spaces
- [ ] `langchain-google-genai` is installed (check build logs)
- [ ] Service has been redeployed after setting key
- [ ] Logs show "✅ Using Google Gemini for LLM"
- [ ] Health endpoint shows `"llm_provider": "gemini"`

---

## 🐛 Still Having Issues?

**Share these details:**
1. **Error message** from logs
2. **Health endpoint response**
3. **What happens** when you test `/agents/monitor`

**Common fixes:**
- Update build command to install `langchain-google-genai`
- Check API key is correct
- Try different model name
- Check Gemini API status

---

**Push the updated code and test!** The fixes should resolve most issues. 🚀

