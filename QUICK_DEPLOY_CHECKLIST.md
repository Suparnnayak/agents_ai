# ✅ Quick Deploy Checklist - OpenAI + Render

## 🎯 5-Minute Deployment

### Before You Start
- [ ] OpenAI account: https://platform.openai.com
- [ ] OpenAI API key copied (starts with `sk-`)
- [ ] Code pushed to GitHub
- [ ] Render account: https://render.com

---

### Step 1: Get OpenAI Key (2 min)
1. Go to https://platform.openai.com
2. Sign up (get $5 free credit)
3. API Keys → Create new key
4. Copy key: `sk-...`

---

### Step 2: Deploy on Render (3 min)
1. Go to https://dashboard.render.com
2. New + → Web Service
3. Connect GitHub repo
4. Set environment variables:
   ```
   AGENT_PREDICTION_API_URL=https://ai-health-agent-vuol.onrender.com/predict
   OPENAI_API_KEY=sk-your_key_here
   ```
5. Create Web Service
6. Wait 2-5 minutes

---

### Step 3: Test (30 sec)
```bash
curl https://your-app.onrender.com/agents/health
```

---

### Step 4: Keep Alive (1 min)
1. Go to https://uptimerobot.com
2. Add monitor:
   - URL: `https://your-app.onrender.com/agents/health`
   - Interval: 5 minutes
3. Done! ✅

---

## ✅ Success Criteria

- [ ] Health endpoint returns 200
- [ ] Full pipeline works
- [ ] UptimeRobot monitor active
- [ ] API URL saved

---

## 🐛 Quick Fixes

**Build fails?** → Check `requirements.txt` has all dependencies

**Service won't start?** → Check environment variables are set

**OpenAI error?** → Verify API key is correct

**Timeout?** → Set up UptimeRobot

---

**See `DEPLOY_OPENAI_RENDER.md` for detailed guide!**

