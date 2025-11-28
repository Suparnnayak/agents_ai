# 🤖 Complete Automation Guide - Zero Manual Intervention

This guide shows you how to set up **fully automated** agent pipeline runs with **zero manual intervention**.

---

## 🎯 What Gets Automated

1. ✅ **Data Fetching** - Automatically gets current data (or uses sample)
2. ✅ **ML Predictions** - Calls your ML API automatically
3. ✅ **Agent Pipeline** - Runs all 4 agents automatically
4. ✅ **Result Saving** - Saves plans to files automatically
5. ✅ **Notifications** - Sends alerts (optional)
6. ✅ **Scheduling** - Runs on schedule (daily, hourly, etc.)

**No manual steps required!** 🚀

---

## 🚀 Option 1: GitHub Actions (Recommended - FREE)

### Setup Steps

#### Step 1: Add Secrets to GitHub

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these secrets:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `AGENT_API_URL` | `https://agents-ai-hfpb.onrender.com/agents/run` | Your agent API URL |
| `ML_API_URL` | `https://ai-health-agent-vuol.onrender.com/predict` | Your ML API URL |
| `HOSPITAL_ID` | `HOSP-123` | Your hospital ID |
| `DISEASE_SENSITIVITY` | `0.5` | Disease sensitivity (0.0-1.0) |
| `DATA_SOURCE` | `sample` | `sample`, `api`, or `file` |
| `NOTIFICATION_WEBHOOK` | (optional) | Slack/Discord webhook URL |

**Optional Secrets (if using external data):**
- `DATA_API_URL` - URL to fetch data from
- `DATA_FILE_PATH` - Path to data file in repo

#### Step 2: Configure Schedule

Edit `.github/workflows/run_agents.yml`:

```yaml
schedule:
  - cron: '0 8 * * *'  # 8 AM UTC daily
```

**Common Schedules:**
- `'0 8 * * *'` - Daily at 8 AM UTC
- `'0 */6 * * *'` - Every 6 hours
- `'0 0,12 * * *'` - Twice daily (midnight and noon)
- `'*/30 * * * *'` - Every 30 minutes

#### Step 3: Push to GitHub

```bash
git add .
git commit -m "Setup automated agent pipeline"
git push
```

**That's it!** GitHub Actions will run automatically on schedule.

---

## 🔄 Option 2: Render Cron Jobs (Free Tier)

### Setup Steps

1. **Create a new Render Cron Job:**
   - Go to Render Dashboard
   - Click **New** → **Cron Job**
   - Name: `hospital-agent-automation`
   - Schedule: `0 8 * * *` (daily at 8 AM UTC)
   - Build Command: `pip install requests`
   - Start Command: `python auto_run_agents.py`

2. **Set Environment Variables:**
   - `AGENT_API_URL`
   - `ML_API_URL`
   - `HOSPITAL_ID`
   - `DISEASE_SENSITIVITY`
   - `DATA_SOURCE`

3. **Deploy**

---

## 🖥️ Option 3: Local Cron Job (Linux/Mac)

### Setup Steps

1. **Make script executable:**
   ```bash
   chmod +x auto_run_agents.py
   ```

2. **Edit crontab:**
   ```bash
   crontab -e
   ```

3. **Add line:**
   ```bash
   # Run daily at 8 AM
   0 8 * * * cd /path/to/project && /usr/bin/python3 auto_run_agents.py >> logs/automation.log 2>&1
   ```

4. **Create logs directory:**
   ```bash
   mkdir -p logs
   ```

---

## 📅 Option 4: Windows Task Scheduler

### Setup Steps

1. **Open Task Scheduler:**
   - Press `Win + R`, type `taskschd.msc`

2. **Create Basic Task:**
   - Name: `Hospital Agent Automation`
   - Trigger: Daily at 8:00 AM
   - Action: Start a program
   - Program: `python`
   - Arguments: `D:\Lets go mumbai\auto_run_agents.py`
   - Start in: `D:\Lets go mumbai`

3. **Set Environment Variables:**
   - In Task Scheduler → Task Properties → Environment Variables
   - Add all required variables

---

## 🌐 Option 5: Cloud Schedulers

### Railway Cron

1. Create `railway.json`:
```json
{
  "cron": {
    "run-agents": {
      "schedule": "0 8 * * *",
      "command": "python auto_run_agents.py"
    }
  }
}
```

### AWS EventBridge / Lambda

1. Create Lambda function with `auto_run_agents.py`
2. Set up EventBridge rule for schedule
3. Configure environment variables

### Google Cloud Scheduler

1. Create Cloud Function with `auto_run_agents.py`
2. Set up Cloud Scheduler job
3. Configure environment variables

---

## 📊 Data Source Options

### Option A: Sample Data (Default)

Uses generated sample data - perfect for testing:

```bash
DATA_SOURCE=sample
```

### Option B: External API

Fetch data from your own API:

```bash
DATA_SOURCE=api
DATA_API_URL=https://your-api.com/data
```

### Option C: File

Load data from a file in your repo:

```bash
DATA_SOURCE=file
DATA_FILE_PATH=samples/sample_request.json
```

---

## 🔔 Notifications (Optional)

### Slack Webhook

1. Create Slack App → Incoming Webhooks
2. Get webhook URL
3. Set `NOTIFICATION_WEBHOOK` secret

### Discord Webhook

1. Discord Server → Settings → Integrations → Webhooks
2. Create webhook, copy URL
3. Set `NOTIFICATION_WEBHOOK` secret

---

## ✅ Verification

### Check GitHub Actions

1. Go to your repo → **Actions** tab
2. You should see "Run Agents Daily" workflow
3. Click on a run to see logs

### Check Results

1. Results are saved to `plans/` directory
2. Files named: `plan_{requestId}_{timestamp}.json`
3. Also uploaded as GitHub artifacts

### Manual Trigger

You can manually trigger from GitHub:
1. Go to **Actions** tab
2. Click "Run Agents Daily"
3. Click "Run workflow"

---

## 🐛 Troubleshooting

### "Workflow not running"

- Check if schedule is correct (UTC time)
- Verify secrets are set
- Check Actions tab for errors

### "API timeout"

- Increase timeout in `auto_run_agents.py`
- Check if APIs are awake (use UptimeRobot)

### "No data found"

- Check `DATA_SOURCE` setting
- Verify `DATA_API_URL` or `DATA_FILE_PATH` is correct

---

## 📈 Advanced: Multiple Hospitals

Run for multiple hospitals:

```yaml
# .github/workflows/run_agents.yml
strategy:
  matrix:
    hospital: [HOSP-123, HOSP-456, HOSP-789]
steps:
  - name: Run for hospital
    env:
      HOSPITAL_ID: ${{ matrix.hospital }}
    run: python auto_run_agents.py
```

---

## 🎯 Summary

**Recommended Setup:**
1. ✅ Use **GitHub Actions** (free, reliable)
2. ✅ Set all secrets in GitHub
3. ✅ Use `DATA_SOURCE=sample` for testing
4. ✅ Schedule: Daily at 8 AM UTC
5. ✅ Enable notifications (optional)

**Result:** Fully automated, zero manual intervention! 🚀

---

**Need help?** Check GitHub Actions logs for detailed error messages!

