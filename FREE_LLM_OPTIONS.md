# 🆓 Free LLM Options for Agents

Since Together.ai now requires credits, here are **FREE alternatives** you can use:

## ✅ Option 1: OpenAI (Recommended - $5 Free Credit)

**Best for**: Easiest setup, reliable, good quality

1. **Sign up**: https://platform.openai.com
2. **Get $5 free credit** (for new users)
3. **Get API key** from dashboard
4. **Cost**: Free for ~2500 requests, then ~$0.002 per request

**Setup:**
```bash
# In Render environment variables
OPENAI_API_KEY=sk-your_key_here
```

**Already supported!** ✅ Your code already works with OpenAI.

---

## ✅ Option 2: Hugging Face Inference API (FREE Tier)

**Best for**: Completely free, no credit card needed

1. **Sign up**: https://huggingface.co
2. **Get API key**: Settings → Access Tokens → New Token
3. **Free tier**: 1000 requests/day (plenty for testing!)

**Setup:**
```bash
# Install package (add to requirements.txt)
pip install langchain-huggingface

# In Render environment variables
HUGGINGFACE_API_KEY=your_hf_token_here
```

**I've updated your code** to support Hugging Face! ✅

---

## ✅ Option 3: Groq (FREE Tier - Very Fast)

**Best for**: Fast responses, free tier available

1. **Sign up**: https://console.groq.com
2. **Get API key** from dashboard
3. **Free tier**: Generous limits

**Setup:**
```bash
# Install package
pip install langchain-groq

# In Render environment variables
GROQ_API_KEY=your_groq_key_here
```

**Note**: Need to add Groq support to code (I can do this if you want)

---

## ✅ Option 4: Use Ollama Locally (100% Free)

**Best for**: No API costs, full control

**Option A: Run Ollama on Your Computer**
- Install Ollama locally
- Keep your computer running
- Set `AGENT_OLLAMA_BASE_URL=http://localhost:11434`
- **Limitation**: Your computer must be on

**Option B: Deploy Ollama on Render (Advanced)**
- Deploy Ollama as separate service
- Requires Starter plan ($7/month) - but Ollama itself is free
- Set `AGENT_OLLAMA_BASE_URL=https://your-ollama-service.onrender.com`

---

## 🎯 Recommended: Start with OpenAI

**Why?**
- ✅ $5 free credit (enough for testing)
- ✅ Already supported in your code
- ✅ Reliable and fast
- ✅ Easy setup

**Steps:**
1. Sign up: https://platform.openai.com
2. Get API key
3. Add to Render: `OPENAI_API_KEY=sk-your_key`
4. Done! ✅

---

## 📊 Comparison

| Service | Free Tier | Setup Difficulty | Quality |
|---------|-----------|------------------|---------|
| **OpenAI** | $5 credit | ⭐ Easy | ⭐⭐⭐⭐⭐ Excellent |
| **Hugging Face** | 1000 req/day | ⭐⭐ Medium | ⭐⭐⭐⭐ Good |
| **Groq** | Generous | ⭐⭐ Medium | ⭐⭐⭐⭐ Good |
| **Ollama Local** | Unlimited | ⭐⭐⭐ Hard | ⭐⭐⭐⭐ Good |

---

## 🚀 Quick Setup Guide

### For OpenAI (Recommended):

1. **Get API Key**:
   - Go to https://platform.openai.com
   - Sign up (get $5 free credit)
   - API Keys → Create new key
   - Copy the key

2. **Add to Render**:
   - Go to your Render service
   - Environment → Add Variable
   - Key: `OPENAI_API_KEY`
   - Value: `sk-your_key_here`

3. **Deploy** ✅

### For Hugging Face:

1. **Get API Key**:
   - Go to https://huggingface.co
   - Sign up
   - Settings → Access Tokens → New Token
   - Copy token

2. **Update requirements.txt**:
   ```bash
   langchain-huggingface>=0.0.1
   ```

3. **Add to Render**:
   - Key: `HUGGINGFACE_API_KEY`
   - Value: `your_hf_token_here`

4. **Deploy** ✅

---

## 💡 My Recommendation

**Start with OpenAI**:
- ✅ Easiest setup
- ✅ $5 free credit (plenty for testing)
- ✅ Already supported
- ✅ Best quality output

**If you run out of credits**, switch to Hugging Face (completely free).

---

## 🔧 Code Already Updated

I've updated `agents/llm_client.py` to support:
- ✅ OpenAI (already supported)
- ✅ Hugging Face (just added!)
- ✅ Together.ai (if you get credits later)
- ✅ Ollama (local or remote)

**Just set the environment variable and it works!** 🎉

---

## 📝 Next Steps

1. **Choose**: OpenAI (easiest) or Hugging Face (free)
2. **Get API key** from chosen service
3. **Add to Render** environment variables
4. **Deploy** ✅

**That's it!** Your agents will work with any of these options.

