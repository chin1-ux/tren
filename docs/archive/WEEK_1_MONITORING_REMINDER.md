# Week 1 Monitoring Reminder

## Deployment Date: August 11, 2026

## Check Date: August 18, 2026 (7 days from deployment)

## Monitoring Task

Run the monitoring script and review results:

```bash
cd backend
python monitor_velocity_enrollment.py
```

## Key Metrics to Review

1. **Dynamic threshold value** - Should be ~1,000,000+ range
2. **Velocity-based enrollments** - Expect ~58 per period (not 910)
3. **Pass rate** - Should be 5-15% range
4. **Promotion rate** - How many velocity-based enrollments become trends
5. **Queue pressure impact** - Any change in queue utilization

## Decision Points After 1 Week

### If Results Are Good (5-15% pass rate, reasonable promotions):
- Continue monitoring
- No queue changes needed
- Revisit Spotify/YouTube question

### If Results Are Poor (pass rate too high/low, queue pressure):
- Adjust percentile threshold (try top 1% or top 10%)
- Consider queue prioritization implementation
- Reassess enrollment criteria

### If No Change/Issues:
- Check if dynamic threshold is calculating correctly
- Verify monitoring script is working
- Check logs for fallback triggers

## Queue Capacity Decision

Only after 1 week of real data:
- Review actual queue pressure vs modeled expectations
- Decide if queue prioritization is needed
- Choose approach (status-based vs frequency-based) if needed

## Spotify/YouTube Integration

Only after 1 week of real data:
- Assess if bug fix alone solved discovery gap
- Determine if external APIs are still necessary
- Rebuild scope based on actual impact

## Files to Reference

- `backend/monitor_velocity_enrollment.py` - monitoring script
- `QUEUE_PRIORITIZATION_SCOPING.md` - queue change options
- `GLOBAL_DISCOVERY_INVESTIGATION_REPORT.md` - external integration plan

## Quick Commands

```bash
# Check monitoring output
cd backend && python monitor_velocity_enrollment.py

# Check queue capacity
cd backend && python check_queue_capacity.py

# Verify threshold calculation
cd backend && python test_dynamic_threshold.py
```

---

**SET REMINDER: Check this file on August 18, 2026**