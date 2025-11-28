# 🚀 Quick Fix: Keep Render API Always Running

## Problem
Your Render API spins down after 15 minutes of inactivity, causing timeouts.

## ✅ Easiest Solution (5 minutes setup)

### Use UptimeRobot (Free, No Code)

1. **Go to**: https://uptimerobot.com
2. **Sign up** (free account)
3. **Click "Add New Monitor"**
4. **Fill in:**
   - Monitor Type: `HTTP(s)`
   - Friendly Name: `Hospital Forecast API`
   - URL: `https://ai-health-agent-vuol.onrender.com/health`
   - Monitoring Interval: `5 minutes`
5. **Click "Create Monitor"**
6. **Done!** ✅

UptimeRobot will ping your API every 5 minutes, keeping it alive.

---

## ✅ Alternative: Self-Hosted Keep-Alive

### Option 1: Run on Your Computer

```bash
# Install requests
pip install requests

# Run the keep-alive script
python keep_alive.py
```

**Keep it running:**
- **Windows**: Run in background or use Task Scheduler
- **Mac/Linux**: Use `nohup python keep_alive.py &`

### Option 2: Use PythonAnywhere (Free)

1. Sign up: https://www.pythonanywhere.com
2. Upload `keep_alive.py`
3. Schedule it to run every 5 minutes
4. Done!

---

## ✅ Best Long-Term Solution: Upgrade Render

**Render Starter Plan: $7/month**
- ✅ No spin-downs
- ✅ Always running
- ✅ Better performance

**Steps:**
1. Go to Render Dashboard
2. Select your service
3. Settings → Plan → Upgrade to "Starter"
4. Done!

---

## ✅ Alternative Platforms (Free, No Spin-Down)

### Railway (Recommended)
- ✅ Free tier with no spin-downs
- ✅ Easy GitHub integration
- ✅ Auto-deploy

**Setup:**
1. Sign up: https://railway.app
2. Connect GitHub repo
3. Deploy automatically
4. Done!

### Fly.io
- ✅ Free tier with no spin-downs
- ✅ Global edge network
- ✅ Fast cold starts

**Setup:**
1. Install: `curl -L https://fly.io/install.sh | sh`
2. Sign up: `fly auth signup`
3. Deploy: `fly launch`
4. Done!

---

## 🎯 Recommendation

**For Now (Immediate Fix):**
→ Use **UptimeRobot** (5 minutes to set up, free forever)

**For Production:**
→ Upgrade Render to **Starter** ($7/month) OR switch to **Railway** (free)

---

## 📝 Quick Command Reference

```bash
# Test your API
curl https://ai-health-agent-vuol.onrender.com/health

# Run keep-alive locally
python keep_alive.py

# Check if API is responding
python -c "import requests; print(requests.get('https://ai-health-agent-vuol.onrender.com/health').json())"
```

