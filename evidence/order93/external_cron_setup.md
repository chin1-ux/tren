# Free External-Cron Setup Guide (Zero-Egress Idempotent Trigger)

To ensure scheduled ticks never drop due to GitHub Actions cron queue latency, you can set up a free external cron job using **cron-job.org**. The internal scraper guard (`check_scraper_guard.py`) guarantees idempotency so premature ticks exit immediately (< 15 seconds) consuming 0 Supabase egress.

---

### Step 1: Create a Fine-Grained GitHub Token
1. Open GitHub $\rightarrow$ **Settings** $\rightarrow$ **Developer settings** $\rightarrow$ **Personal access tokens** $\rightarrow$ **Fine-grained tokens**.
2. Click **Generate new token**:
   - **Token name**: `trendrop-external-cron`
   - **Expiration**: 90 days (or custom)
   - **Resource owner**: `chin1-ux`
   - **Repository access**: "Only select repositories" $\rightarrow$ choose `chin1-ux/tren`
   - **Permissions** $\rightarrow$ **Repository permissions**:
     - **Actions**: `Read and write` (required to trigger `workflow_dispatch`)
     - **Metadata**: `Read-only` (selected automatically)
3. Click **Generate token** and copy the secret token.

---

### Step 2: Configure Cron-Job.org
1. Create a free account at [cron-job.org](https://cron-job.org).
2. Go to **Cronjobs** $\rightarrow$ **Create cronjob**.
3. Fill in the details:
   - **Title**: `Trendrop Dedicated Scraper Trigger`
   - **URL**: `https://api.github.com/repos/chin1-ux/tren/actions/workflows/scraper_cron.yml/dispatches`
   - **Execution schedule**: Every 30 minutes (or every 60 minutes)
   - **HTTP Method**: `POST`
4. In **Headers**:
   - `Accept`: `application/vnd.github.v3+json`
   - `Authorization`: `Bearer YOUR_FINE_GRAINED_TOKEN`
   - `User-Agent`: `TrendropExternalCron/1.0`
   - `Content-Type`: `application/json`
5. In **Request Body**:
   ```json
   {"ref": "main"}
   ```
6. Click **Save**.

---

### Why It Is 100% Safe & Cost-Free:
- If a tick arrives when less than the configured gap has passed (e.g., within 360m), `check_scraper_guard.py` evaluates the elapsed time from the last executed run, outputs `Scraper guard decision: SKIP`, and terminates the job in ~15 seconds without touching Supabase or running heavy scrapers.
- As soon as the threshold (e.g. 360m or 165m) is reached, the very next tick runs the full pipeline.
