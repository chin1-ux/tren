import json
from datetime import datetime, timezone

def run_guard_simulation():
    ticks = [
        {"id": "39039845286", "time": "2026-10-17T14:13:44Z", "is_real_run": True, "event": "schedule"},
        {"id": "39053040589", "time": "2026-10-17T17:16:38Z", "event": "schedule"},
        {"id": "39062715163", "time": "2026-10-17T19:29:58Z", "event": "schedule"},
        {"id": "39074828271", "time": "2026-10-17T22:22:48Z", "event": "schedule"},
        {"id": "39085269151", "time": "2026-10-18T01:06:39Z", "event": "schedule"},
        {"id": "39102355951", "time": "2026-10-18T05:58:03Z", "event": "schedule"},
        {"id": "39104754603", "time": "2026-10-18T06:38:27Z", "event": "workflow_dispatch"},
    ]

    thresholds = [165, 360, 600]
    results = {}

    for t in thresholds:
        last_real_time = datetime.fromisoformat(ticks[0]["time"].replace("Z", "+00:00"))
        log = []
        for i, tick in enumerate(ticks[1:], start=1):
            curr_time = datetime.fromisoformat(tick["time"].replace("Z", "+00:00"))
            gap_minutes = (curr_time - last_real_time).total_seconds() / 60.0
            
            if tick["event"] == "workflow_dispatch":
                action = "PROCEED (manual workflow_dispatch bypasses guard)"
                last_real_time = curr_time
            elif gap_minutes >= t:
                action = f"PROCEED (gap {gap_minutes:.1f}m >= {t}m threshold)"
                last_real_time = curr_time
            else:
                action = f"SKIP (gap {gap_minutes:.1f}m < {t}m threshold)"
                
            log.append({
                "tick_id": tick["id"],
                "time": tick["time"],
                "gap_from_last_real_minutes": round(gap_minutes, 1),
                "threshold": t,
                "action": action
            })
        results[f"threshold_{t}m"] = log

    # Save to evidence
    import os
    os.makedirs("evidence/order93", exist_ok=True)
    with open("evidence/order93/guard_simulation_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("Guard simulation completed across thresholds 165m, 360m, 600m:")
    for t in thresholds:
        print(f"\n--- Threshold {t}m ---")
        for entry in results[f"threshold_{t}m"]:
            print(f"[{entry['time']}] Run {entry['tick_id']}: gap={entry['gap_from_last_real_minutes']}m -> {entry['action']}")

if __name__ == "__main__":
    run_guard_simulation()
