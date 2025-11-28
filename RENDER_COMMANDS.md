# 🔧 Render Build & Start Commands

## For Agent API Deployment

### Build Command
```bash
pip install -r requirements.txt
```

**Or if you need OpenAI support:**
```bash
pip install -r requirements.txt && pip install langchain-openai
```

### Start Command
```bash
python agent_api_server.py
```

---

## 📝 How to Set in Render

### Option 1: Using render_agents.yaml (Auto-Detected)

If you have `render_agents.yaml` in your repo, Render will auto-detect it:

```yaml
services:
  - type: web
    name: hospital-agent-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python agent_api_server.py
```

**Render will use these automatically!** ✅

---

### Option 2: Manual Setup in Render Dashboard

If Render doesn't auto-detect, set manually:

1. **Go to Render Dashboard** → Your Service → Settings
2. **Build Command**:
   ```
   pip install -r requirements.txt
   ```
   
   **Or with OpenAI:**
   ```
   pip install -r requirements.txt && pip install langchain-openai
   ```

3. **Start Command**:
   ```
   python agent_api_server.py
   ```

---

## 🔍 Quick Reference

| Setting | Command |
|---------|---------|
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python agent_api_server.py` |
| **Health Check Path** | `/agents/health` |
| **Port** | Auto-set by Render (don't hardcode) |

---

## ⚠️ Important Notes

1. **Port**: Don't hardcode port! Render sets `PORT` environment variable automatically
   - Your code already handles this: `PORT = int(os.getenv("PORT", "5001"))` ✅

2. **Python Version**: Render auto-detects Python 3, but you can specify in `runtime.txt`:
   ```
   python-3.10.12
   ```

3. **OpenAI Package**: If using OpenAI, you might need to install `langchain-openai`:
   - Add to build command: `pip install -r requirements.txt && pip install langchain-openai`
   - Or add to `requirements.txt`: `langchain-openai>=0.1.0`

---

## ✅ Verification

After deployment, check logs to verify:
- ✅ Build completed successfully
- ✅ All packages installed
- ✅ Service started on correct port
- ✅ Health endpoint accessible

---

**That's it!** These are the commands you need. 🚀

