# 🔧 Gemini Troubleshooting - What Issues Are You Seeing?

## ✅ What I've Fixed

1. ✅ **Response format handling** - Gemini returns `AIMessage` objects, not strings
2. ✅ **Better error messages** - More detailed error logging
3. ✅ **Improved JSON extraction** - Better parsing
4. ✅ **Error handling** - More robust exception handling

---

## 🔍 Common Issues - Tell Me Which One

### Issue A: Import Error
**Error**: `ModuleNotFoundError: No module named 'langchain_google_genai'`

**Solution**: 
- Update build command: `pip install -r requirements.txt && pip install langchain-google-genai`
- Or add to requirements.txt (already done)

---

### Issue B: Response Format Error
**Error**: `AttributeError` or `'AIMessage' object has no attribute...`

**Solution**: ✅ **Fixed!** Code now handles Gemini's response format automatically

---

### Issue C: API Key Not Working
**Error**: Still using Ollama, not Gemini

**Check**:
- Environment variable: `GOOGLE_API_KEY` (not `GEMINI_API_KEY`)
- Key format: Starts with `AIza...`
- Service redeployed after setting key

---

### Issue D: JSON Parsing Error
**Error**: `OutputParserException: Failed to parse JSON`

**Solution**: ✅ **Improved!** Better JSON extraction and error messages

---

### Issue E: Rate Limit
**Error**: `429 RESOURCE_EXHAUSTED`

**Solution**: 
- Free tier: 60 requests/minute
- Wait a moment and retry
- Check quota at https://aistudio.google.com/app/apikey

---

## 📋 What I Need From You

**Please share:**
1. **Exact error message** from Render logs
2. **What happens** when you call `/agents/run`
3. **Health endpoint response** (does it show `"llm_provider": "gemini"`?)

---

## 🧪 Quick Test

Test the simplest endpoint first:

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

**Share the response** - this will help identify the issue!

---

## ✅ Next Steps

1. **Push updated code** (I've fixed response handling)
2. **Share the error** you're seeing
3. **Test the monitor endpoint** above
4. **Check Render logs** for specific errors

---

**What specific error are you seeing?** Share the error message and I'll help fix it! 🚀

