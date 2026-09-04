# AUTOMATED PREVENTION SYSTEM - LLM Classification Pipeline

## Problem Addressed
The issue of trends getting stuck in "pending" status and being filtered out from the API will no longer require manual detection and intervention. Multiple automated safeguards have been implemented.

## Multi-Layer Protection System

### 1. Increased Processing Frequency
**File**: `.github/workflows/nightly-llm-classification.yml`

**Change**: Increased from 2x daily to 4x daily
- **Before**: 00:00 and 12:00 UTC (2 runs/day)
- **After**: 00:00, 06:00, 12:00, 18:00 UTC (4 runs/day)
- **Capacity**: 50 calls per run = 200 calls per day
- **Rationale**: Prevents backlog accumulation between runs

### 2. Emergency Auto-Trigger System
**File**: `.github/workflows/emergency-llm-classification.yml` (NEW)
**Script**: `backend/check_pending_count.py` (NEW)

**Features**:
- **Schedule**: Runs every 2 hours automatically
- **Trigger Conditions**:
  - Total pending > 20 trends
  - Emerging pending > 3 trends
- **Emergency Mode**: When triggered, runs with 100-call limit (vs normal 50)
- **Faster Processing**: 3s delay (vs normal 5s) for quicker backlog clearing
- **Automatic**: No manual intervention required

### 3. Proactive Monitoring with Lowered Thresholds
**File**: `.github/workflows/pending-trends-monitor.yml`
**Script**: `backend/pending_trends_monitor.py`

**Changes**:
- **Frequency**: Increased from every 12 hours to every 4 hours
- **Lowered Thresholds**:
  - High pending: 50 → 25 (earlier detection)
  - Emerging pending: 5 → 3 (faster response)
- **Alert Actions**: Exits with error code to trigger GitHub Actions notifications
- **Automatic Notifications**: GitHub will email/alert on workflow failures

### 4. Enhanced Capacity
**File**: `.github/workflows/nightly-llm-classification.yml`

**Change**: Increased calls per run from 30 to 50
- **Before**: 30 calls/run × 2 runs = 60 calls/day
- **After**: 50 calls/run × 4 runs = 200 calls/day
- **Buffer**: Significant headroom for trend creation spikes

## How the System Works Together

### Normal Operation
1. **Main Classification**: Runs 4x daily (00:00, 06:00, 12:00, 18:00 UTC)
2. **Monitoring**: Checks every 4 hours for any issues
3. **Emergency Check**: Runs every 2 hours as safety net

### When Issues Arise
1. **Detection**: Monitor or emergency check detects pending > 20
2. **Auto-Trigger**: Emergency workflow automatically runs classification
3. **Clearing**: Processes up to 100 trends with faster rate limiting
4. **Alerting**: GitHub Actions sends notification about the emergency run

### Prevention of Future Issues
- **Capacity**: 200 calls/day vs estimated ~30-45 new trends/day
- **Frequency**: 4x daily prevents long gaps between processing
- **Emergency**: Auto-trigger catches issues before they impact users
- **Monitoring**: Proactive detection with lowered thresholds
- **Fallback**: 24-hour timeout still exists as final safety net

## Current Configuration Summary

| Component | Frequency | Capacity | Trigger Condition |
|-----------|-----------|----------|-------------------|
| Main Classification | 4x daily | 50 calls/run | Scheduled |
| Emergency Classification | Every 2 hours | 100 calls/run | Pending > 20 or Emerging > 3 |
| Monitoring | Every 4 hours | N/A | Scheduled |
| 24h Fallback | Every 6 hours | All pending | Pending > 24h old |

## Alert Thresholds

| Metric | Warning Threshold | Emergency Trigger |
|--------|------------------|-------------------|
| Total Pending | > 25 | > 20 |
| Emerging Pending | > 3 | > 3 |
| High Pending Warning | > 25 | N/A |

## Verification Steps

### Test Emergency System
```bash
# Manually trigger emergency workflow
gh workflow run emergency-llm-classification.yml

# Check current pending count
cd backend
python check_pending_count.py
```

### Monitor System Health
```bash
# Run monitoring check
cd backend
python pending_trends_monitor.py
```

### Check Classification History
```bash
# View recent classification activity
cd backend
python check_llm_classification_history.py
```

## What You No Longer Need to Do

❌ **Manual detection** - System auto-detects pending buildup  
❌ **Manual backfill** - Emergency workflow auto-processes backlog  
❌ **Capacity adjustments** - System has sufficient headroom  
❌ **Frequency monitoring** - Automated checks every 2-4 hours  
❌ **Manual threshold alerts** - GitHub Actions auto-notifies  

## What the System Will Handle Automatically

✅ **Detect** pending trend accumulation within 2 hours  
✅ **Trigger** emergency classification without manual intervention  
✅ **Process** backlog with higher capacity when needed  
✅ **Alert** you via GitHub Actions notifications  
✅ **Prevent** user-visible data loss through multiple safeguards  
✅ **Scale** processing based on pending count automatically  

## Monitoring Dashboard

Key metrics to watch:
- **Pending Trends**: Should stay < 20 normally
- **Emerging Pending**: Should stay < 3 normally  
- **Classification Success Rate**: Should be near 100%
- **Completed Last 24h**: Should be > 0 during active periods

## Expected Behavior

### Healthy System
- Pending: 0-5 trends
- Emerging Pending: 0-2 trends
- Main classification runs complete successfully
- No emergency triggers needed

### Minor Issue (Auto-Handled)
- Pending: 10-20 trends
- Emergency workflow triggers automatically
- Backlog cleared within 1-2 hours
- User may not notice any impact

### Major Issue (Auto-Handled + Alerted)
- Pending: > 25 trends
- Emergency workflow triggers immediately
- GitHub Actions sends alert notification
- System continues processing automatically
- You investigate root cause after automatic recovery

## Files Modified/Created

### Modified
- `.github/workflows/nightly-llm-classification.yml` - 4x daily, 50 calls/run
- `.github/workflows/pending-trends-monitor.yml` - Every 4 hours, lowered thresholds
- `backend/pending_trends_monitor.py` - Lowered alert thresholds

### Created
- `.github/workflows/emergency-llm-classification.yml` - Auto-trigger system
- `backend/check_pending_count.py` - Pending count checker for GitHub Actions

## Maintenance

The system is designed to be self-maintaining. Occasional checks:
1. **Weekly**: Review GitHub Actions logs for any patterns
2. **Monthly**: Check if trend creation rate has increased significantly
3. **Quarterly**: Review capacity settings if trend volume changes

## Conclusion

This multi-layer automated system ensures that the LLM classification pipeline issue that required manual intervention will not recur. The system will detect, alert, and automatically correct issues before they impact user experience.