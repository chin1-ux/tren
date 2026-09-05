# RECLASSIFICATION INCIDENT - August 14, 2026

## Issue Summary
The Rising trends count in the frontend reduced again due to a recurrence of the LLM classification pipeline issue. New trends were accumulating in "pending" status and being filtered out by the strict API filter.

## Root Cause Analysis
1. **Backlog Accumulation**: 51 trends were stuck in "pending" status across all statuses
2. **Rising Impact**: 9 of 31 Rising trends were pending, causing API to return only 22 trends
3. **Emerging Impact**: 11 Emerging trends were pending, indicating insufficient processing cadence
4. **Insufficient Capacity**: The GitHub Actions workflow was limited to 30 calls per run, which couldn't keep up with trend creation volume

## Investigation Timeline
- **12:38 UTC**: Detected issue - Rising trends showing reduced count
- **12:38 UTC**: Database check showed 31 Rising trends total, but classification analysis showed 9 pending
- **12:38 UTC**: Monitoring alert triggered: 51 pending trends total, 11 Emerging pending
- **12:38 UTC**: Ran manual backfill with 50-call limit - processed 50 trends successfully
- **12:42 UTC**: Ran second backfill to clear remaining 1 pending trend
- **12:42 UTC**: Updated GitHub Actions workflow to increase capacity from 30 to 50 calls per run

## Resolution Actions

### 1. Immediate Backfill
- **Processed**: 51 pending trends in 2 manual runs
- **Success Rate**: 100% (51/51 succeeded)
- **Duration**: ~3.5 minutes total
- **Result**: All pending trends converted to "completed"

### 2. Capacity Increase
**File Modified**: `.github/workflows/nightly-llm-classification.yml`
- **Before**: `NIGHTLY_LLM_MAX_CALLS_PER_RUN: 30`
- **After**: `NIGHTLY_LLM_MAX_CALLS_PER_RUN: 50`
- **Rationale**: The twice-daily schedule with 30-call limit couldn't keep up with trend creation volume

### 3. Current State
- **Rising Trends**: 31 total, 30 completed, 1 not_needed, 0 pending
- **Emerging Trends**: 33 total, all classified, 0 pending
- **Overall Pending**: 0
- **Emerging Pending**: 0
- **API Verification**: All 31 Rising trends now returned by API

## Prevention Measures

### Monitoring Improvements
The existing monitoring system correctly detected the issue:
- **Total Pending Alert**: Triggered at 51 > 50 threshold
- **Emerging Alert**: Triggered at 11 > 5 threshold
- **Recommendation**: System correctly suggested increasing processing frequency

### Capacity Planning
- **Current Schedule**: Twice daily (00:00 and 12:00 UTC)
- **Current Capacity**: 50 calls per run = 100 calls per day
- **Trend Creation Rate**: ~10-15 trends per 8-hour scraper run
- **Buffer**: The 50-call limit provides headroom for backlog clearing

### Future Monitoring Points
1. **Watch Emerging**: If Emerging pending exceeds 5 consistently, consider 4x daily schedule
2. **Rate Limit Awareness**: Monitor Groq API rate limits during high-volume periods
3. **Workflow Logs**: Check GitHub Actions logs for any failures or timeouts
4. **Trend Velocity**: Monitor if trend creation rate increases beyond current capacity

## Technical Details

### Classification Pipeline
- **LLM Provider**: Groq API with 3 configured keys
- **Rate Limiting**: 5s base delay, exponential backoff
- **Success Rate**: 100% during backfill (no rate limit errors)
- **Retry Logic**: 3 attempts per trend before marking as llm_unavailable

### API Filter Policy
- **Current Filter**: `["completed", "not_needed", "skipped_local_fallback"]`
- **Strict Mode**: "pending" excluded to prevent showing unenriched trends
- **Fallback**: 24-hour timeout converts pending → not_needed for visibility

### Trend Status Distribution (Post-Fix)
- **Rising**: 30 completed, 1 not_needed
- **Emerging**: 25 completed, 8 not_needed  
- **Peaked**: 153 completed, 128 not_needed
- **Expired**: 88 completed, 147 not_needed, 3 skipped_local_fallback

## Lessons Learned

1. **Capacity Planning**: The initial 30-call limit was insufficient for the trend creation volume
2. **Monitoring Effectiveness**: The alert system correctly identified the issue before it became critical
3. **Graceful Degradation**: The 24-hour fallback provides safety net but shouldn't be relied upon
4. **Trend Velocity**: Emerging trends can accumulate quickly if processing cadence is insufficient

## Recommendations

1. **Continue Monitoring**: Check Emerging pending count daily for next week
2. **Consider Frequency**: If Emerging pending exceeds 5 consistently, increase to 4x daily
3. **Review Capacity**: If trend creation rate increases, consider per-run limit adjustment
4. **Automate Scaling**: Consider dynamic capacity adjustment based on pending count

## Recovery Verification

✅ **Database**: All 31 Rising trends classified  
✅ **API**: All 31 Rising trends returned  
✅ **Monitoring**: No pending trends detected  
✅ **Capacity**: Increased to 50 calls per run  
✅ **Emerging**: No pending accumulation  

**Status**: ✅ RESOLVED - All systems operational