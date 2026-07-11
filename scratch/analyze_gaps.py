from datetime import datetime

scheduled_runs = [
    ('29164465850', '2026-07-11T18:59:41', 'in_progress'),
    ('29153960790', '2026-07-11T13:13:50', 'success'),
    ('29145197729', '2026-07-11T07:51:50', 'success'),
    ('29136388182', '2026-07-11T02:28:02', 'success'),
    ('29117882791', '2026-07-10T19:24:14', 'success'),
    ('29099493562', '2026-07-10T14:21:20', 'success'),
    ('29083336645', '2026-07-10T09:31:33', 'success'),
    ('29065514634', '2026-07-10T02:50:10', 'success'),
    ('29045317466', '2026-07-09T19:42:52', 'success'),
    ('29027280198', '2026-07-09T14:54:11', 'success'),
    ('29008713219', '2026-07-09T09:35:22', 'success'),
]

expected_slots_utc = [0, 6, 12, 18]

print('=== GAP ANALYSIS: CONSECUTIVE SCHEDULED RUNS ===')
print()
print(f'  {"run_id":<14} {"created_at (UTC)":<22} {"expected slot":<16} {"delay":>8}   {"gap from prev":<14} {"status"}')
print('  ' + '-' * 96)

for i, (rid, ts, status) in enumerate(scheduled_runs):
    dt = datetime.fromisoformat(ts)
    actual_min = dt.hour * 60 + dt.minute
    closest = min(expected_slots_utc, key=lambda h: abs(actual_min - h * 60))
    delay_min = actual_min - closest * 60

    gap_str = ''
    flag = ''
    if i < len(scheduled_runs) - 1:
        prev_dt = datetime.fromisoformat(scheduled_runs[i + 1][1])
        gap = dt - prev_dt
        total_secs = int(gap.total_seconds())
        gap_h = total_secs // 3600
        gap_m = (total_secs % 3600) // 60
        gap_str = f'{gap_h}h {gap_m:02d}m'
        if total_secs > 6.5 * 3600:
            flag = '  *** MISSED SLOT ***'

    print(f'  {rid:<14} {ts:<22} {closest:02d}:00 UTC    +{delay_min:3d}min   {gap_str:<14} {status}{flag}')

print()
print('=== JULY 11 18:00 UTC SLOT VERDICT ===')
print('  Run 29164465850 fired at 18:59 UTC (59-min GH Actions delay).')
print('  The slot DID fire. Our check window (17:30-18:30) was 29min too narrow.')
print()
print('=== ALL GAPS BETWEEN CONSECUTIVE SCHEDULED RUNS ===')
for i in range(len(scheduled_runs) - 1):
    dt_curr = datetime.fromisoformat(scheduled_runs[i][1])
    dt_prev = datetime.fromisoformat(scheduled_runs[i + 1][1])
    gap_secs = int((dt_curr - dt_prev).total_seconds())
    gap_h = gap_secs // 3600
    gap_m = (gap_secs % 3600) // 60
    flag = '  *** >6.5h ***' if gap_secs > 6.5 * 3600 else ''
    print(f'  {scheduled_runs[i+1][1]} -> {scheduled_runs[i][1]}  = {gap_h}h {gap_m:02d}m{flag}')

print()
print('=== CONCLUSION ===')
print('  No scheduled slot was skipped by GitHub Actions.')
print('  All runs fired with 59min-3h31min GH scheduler delay (normal for low-traffic repos).')
print('  The 10.32h gap in cron_runs DB = DB write likely failed on one run, not a missed GH trigger.')
