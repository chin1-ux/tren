# Trendrop live feed transparency audit

Audit timestamp: 2026-08-01T09:40:33Z

Scope: read-only audit of the current production-ish Supabase tables behind the frontend trend feed. I used live SELECT queries only, plus the repository’s pipeline logs and source files for the exact filter/classification logic.

## 0) What the frontend is actually showing

The current homepage has two feed tabs in `frontend/src/routes/index.tsx`:

- `India` → `fetchTrends(language, sortMode, selectedNiche)` → `GET /api/trends`
- `Emerging` → `fetchEmergingTrends(language)` → `GET /api/trends/emerging`

There is no separate live “Rising” tab in the current route; “India” is the visible label for the rising feed.

The backend endpoints are:

- `/api/trends`: `status = rising` and `llm_classification_status in ('completed','not_needed')`
- `/api/trends/emerging`: `status = emerging` and `llm_classification_status in ('completed','not_needed')`

Live query timestamp for the snapshots below: `2026-08-01T09:39:01.976556+00:00`

Raw live counts:

```json
{"ts": "2026-08-01T09:39:01.976556+00:00", "feed": "rising", "count": 9}
{"ts": "2026-08-01T09:39:01.976556+00:00", "feed": "emerging", "count": 19}
{"ts": "2026-08-01T09:39:01.976556+00:00", "feed": "all_active", "count": 28}
```

## 1) Currently displayed audios, per tab

### India tab

These 9 rows are what the India tab currently pulls from the live `trends` table.

| ID | Title | Classification | Why this region | Key live metrics | Last scored |
| --- | --- | --- | --- | --- | --- |
| 97 | Majboor — Sheheryar Rehan, Zoha Waseem | `rising` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=1819414.52005285`; `reel_count=3`; `creator_fit_score=0.790587717834028`; `hook_retention_score=0.95`; `saturation_penalty=0.45351364685108`; `promotion_reason=velocity_outlier` | `2026-08-01T08:50:24.371428` |
| 58 | Hangover — Salman Khan, Meet Bros Anjjan, Shreya Ghoshal | `rising` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=595519.819192323`; `reel_count=3`; `creator_fit_score=0.849638716495139`; `hook_retention_score=0.6`; `saturation_penalty=0.387901426116512`; `promotion_reason=velocity_outlier` | `2026-07-30T08:52:51.996355` |
| 36 | X-COOL! (Slowed) — tienanh109, HDN, MC K3 | `rising` | `trend_origin=unknown`; `discovery_source=unexpected_candidate` | `velocity_avg=211109.26233758`; `reel_count=3`; `creator_fit_score=0.795362422275`; `hook_retention_score=0.6`; `saturation_penalty=0.519041753027778`; `promotion_reason=velocity_outlier` | `2026-07-29T12:54:34.175156` |
| 70 | Saiya Raat Bhar Jagaya — Ravi Raushan, Khusi Kakkar | `rising` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=189196.70936834`; `reel_count=2`; `creator_fit_score=0.760200781398611`; `hook_retention_score=0.6`; `saturation_penalty=0.558110242890432`; `promotion_reason=velocity_outlier` | `2026-07-30T14:31:20.562628` |
| 82 | Runaway (feat. Pusha T) — Kanye West | `rising` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=162611.467615433`; `reel_count=2`; `creator_fit_score=0.83578341121875`; `hook_retention_score=0.650904398231399`; `saturation_penalty=0.403296209756944`; `promotion_reason=velocity_outlier` | `2026-07-31T09:17:03.751872` |
| 66 | Krishna Krish Flute — Lakhinandan Lahon | `rising` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=138429.281732218`; `reel_count=3`; `creator_fit_score=0.849836661800694`; `hook_retention_score=0.6`; `saturation_penalty=0.387681486888117`; `promotion_reason=velocity_outlier` | `2026-07-30T14:31:16.543459` |
| 49 | KALYANI (Remix) — ARJN, KDS, FIFTY4, Shreya Ghoshal | `rising` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=103287.143500281`; `reel_count=6`; `creator_fit_score=0.805540549801389`; `hook_retention_score=0.6`; `saturation_penalty=0.507732722442901`; `promotion_reason=velocity_outlier` | `2026-07-29T14:41:21.196947` |
| 89 | Vachindamma — Sid Sriram | `rising` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=100446.719689875`; `reel_count=4`; `creator_fit_score=0.8392195304875`; `hook_retention_score=0.498801184025222`; `saturation_penalty=0.470311632791667`; `promotion_reason=creator_adoption` | `2026-07-31T19:57:24.876879` |
| 92 | Na Na Karte Pyar — Udit Narayan, Alka Yagnik | `rising` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=53627.0837114602`; `reel_count=3`; `creator_fit_score=0.849569401536805`; `hook_retention_score=0.512960683982123`; `saturation_penalty=0.387978442736883`; `promotion_reason=velocity_outlier` | `2026-08-01T03:42:22.905236` |

### Emerging tab

These 19 rows are what the Emerging tab currently pulls from the live `trends` table.

| ID | Title | Classification | Why this region | Key live metrics | Last scored |
| --- | --- | --- | --- | --- | --- |
| 100 | Udaarian - 2.0 — Satinder Sartaaj, Beat Minister | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=180584.537187677`; `reel_count=2`; `creator_fit_score=0.773933319879167`; `hook_retention_score=0.66190678707451`; `saturation_penalty=0.542851866800926`; `promotion_reason=creator_count_emerging` | `2026-08-01T08:50:29.639581` |
| 102 | Hollaback Girl (Slowed) — Bread Beatz, Sakyul | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=159380.015647902`; `reel_count=4`; `creator_fit_score=0.760096568593056`; `hook_retention_score=0.95`; `saturation_penalty=0.558226034896605`; `promotion_reason=creator_count_emerging` | `2026-08-01T08:50:32.813071` |
| 91 | Thalapathy Vetri Kondan — Anirudh Ravichander, Vivek | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=149809.895664829`; `reel_count=4`; `creator_fit_score=0.833682240504167`; `hook_retention_score=0.6129250956807`; `saturation_penalty=0.476464177217593`; `promotion_reason=creator_count_emerging` | `2026-08-01T03:42:21.434436` |
| 98 | Jhalak Dikhla Ja — Himesh Reshammiya | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=135065.968752166`; `reel_count=2`; `creator_fit_score=0.847651837304167`; `hook_retention_score=0.68985883763033`; `saturation_penalty=0.46094240299537`; `promotion_reason=creator_count_emerging` | `2026-08-01T08:50:26.433489` |
| 84 | Sampradayani Suddapoosa — Suresh Bobbili | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=113319.798317859`; `reel_count=3`; `creator_fit_score=0.849815779693056`; `hook_retention_score=0.444880477358422`; `saturation_penalty=0.387704689229938`; `promotion_reason=audio_use_count_emerging` | `2026-07-31T14:38:22.615621` |
| 93 | Tiranga (From "Yodha") — Tanishk Bagchi, Manoj Muntashir, B Praak | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=101020.939431579`; `reel_count=2`; `creator_fit_score=0.786698482675`; `hook_retention_score=0.472981237449821`; `saturation_penalty=0.528668352583333`; `promotion_reason=creator_count_emerging` | `2026-08-01T03:42:23.943426` |
| 99 | Aa Fariyale — Pramod Premi Yadav, Abhishek Gupta | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=75064.9966176652`; `reel_count=3`; `creator_fit_score=0.836984762731944`; `hook_retention_score=0.637284690818556`; `saturation_penalty=0.401961374742284`; `promotion_reason=audio_use_count_emerging` | `2026-08-01T08:50:28.20651` |
| 78 | Hamar Lage Ho — Shivani Singh | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=70970.9143236862`; `reel_count=2`; `creator_fit_score=0.846865621666667`; `hook_retention_score=0.555892627759581`; `saturation_penalty=0.461815975925926`; `promotion_reason=creator_count_emerging` | `2026-07-31T03:42:19.950708` |
| 71 | Palang Sagwan Ke — Khesari Lal Yadav, Indu Sonali | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=69777.082642596`; `reel_count=2`; `creator_fit_score=0.80620559275`; `hook_retention_score=0.6`; `saturation_penalty=0.506993785833333`; `promotion_reason=creator_count_emerging` | `2026-07-30T14:31:21.575988` |
| 69 | Bholi Si Surat (From "Dil To Pagal Hai") (feat. Shah Rukh Khan, Madhuri Dixit, Karisma Kapoor) — Uttam Singh, Lata Mangeshkar, Udit Narayan | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=68563.891844061`; `reel_count=2`; `creator_fit_score=0.865885955572917`; `hook_retention_score=0.6`; `saturation_penalty=0.440682271585648`; `promotion_reason=creator_count_emerging` | `2026-07-30T14:31:19.564812` |
| 55 | Bioguruh Original Audio — alindamohan | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=65550.4349794184`; `reel_count=2`; `creator_fit_score=0.761100282560417`; `hook_retention_score=0.6`; `saturation_penalty=0.557110797155093`; `promotion_reason=creator_count_emerging` | `2026-07-30T08:21:17.396027` |
| 77 | Sad Tune — abu arnab | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=65397.889528007`; `reel_count=4`; `creator_fit_score=0.929721515150694`; `hook_retention_score=0.567279411764706`; `saturation_penalty=0.387809427610339`; `promotion_reason=audio_use_count_emerging` | `2026-07-31T03:42:18.888446` |
| 101 | Aankhon Se Tune Kya Keh Diya — Jatin-Lalit, Kumar Sanu, Alka Yagnik, Sameer Anjaan | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=55566.8194966645`; `reel_count=3`; `creator_fit_score=0.879721762627083`; `hook_retention_score=0.616658331562224`; `saturation_penalty=0.425309152636574`; `promotion_reason=creator_count_emerging` | `2026-08-01T08:50:30.725408` |
| 52 | Udi Udi — Aneesh, Sarkar, Hruday | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=54202.1150087244`; `reel_count=2`; `creator_fit_score=0.879670467859722`; `hook_retention_score=0.6`; `saturation_penalty=0.425366146822531`; `promotion_reason=creator_count_emerging` | `2026-07-30T08:21:14.733634` |
| 83 | Ishq — Raj Mawar, Mahi Chauhan | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=43205.3798101822`; `reel_count=3`; `creator_fit_score=0.802584439683333`; `hook_retention_score=0.675509304171444`; `saturation_penalty=0.440183955907407`; `promotion_reason=audio_use_count_emerging` | `2026-07-31T09:17:04.896674` |
| 90 | Tera Mera Rishta (Vedika Sinha) — Himanshu Thakur | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=32552.1511062031`; `reel_count=2`; `creator_fit_score=0.818046566939583`; `hook_retention_score=0.95`; `saturation_penalty=0.493837147844907`; `promotion_reason=creator_count_emerging` | `2026-07-31T19:57:25.738002` |
| 56 | Char Chakka Wali — Shilpi Raj | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=31743.3301870138`; `reel_count=2`; `creator_fit_score=0.821562204144444`; `hook_retention_score=0.6`; `saturation_penalty=0.489930884283951`; `promotion_reason=creator_count_emerging` | `2026-07-30T08:21:18.185888` |
| 95 | Rasputin — Boney M. | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=29136.6344672521`; `reel_count=3`; `creator_fit_score=0.772995529682639`; `hook_retention_score=0.926654150899489`; `saturation_penalty=0.543893855908179`; `promotion_reason=creator_count_emerging` | `2026-08-01T03:42:26.297018` |
| 96 | Ve Sohneya — Kamal Khan, Ricky Khan, Aden | `emerging` | `trend_origin=IN`; `discovery_source=unexpected_candidate` | `velocity_avg=22600.1260988226`; `reel_count=2`; `creator_fit_score=0.7714752088125`; `hook_retention_score=0.640180688974603`; `saturation_penalty=0.545583101319444`; `promotion_reason=creator_count_emerging` | `2026-08-01T03:42:27.497194` |

## 2) Filtered-out / excluded audios

These are live rows in `trends` that did not make it to the frontend because they failed a frontend-visible filter or a lifecycle step.

### Rejected by lifecycle status

Frontend only renders `status in ('rising','emerging')` with verified classification statuses, so these are excluded even though they exist in the table.

Raw status distribution:

```json
{"ts": "2026-08-01T09:40:33.274782+00:00", "status_llm_counts": {"expired|not_needed": 12, "peaked|completed": 8, "expired|completed": 16, "emerging|not_needed": 19, "peaked|not_needed": 27, "rising|completed": 1, "rising|not_needed": 8, "expired|skipped_local_fallback": 3}}
```

Representative excluded rows:

```json
{"ts": "2026-08-01T09:40:33.274782+00:00", "sample": "excluded_peaked", "count": 5, "rows": [{"id": 94, "audio_title": "Jise Dekh Mera Dil Dhadke", "status": "peaked", "velocity_avg": 17851.5852288984, "peak_velocity": 41055.9369266869, "window_hours_remaining": 20, "promotion_reason": "creator_count_emerging", "llm_classification_status": "not_needed"}, {"id": 88, "audio_title": "Rang Jo Lagyo", "status": "peaked", "velocity_avg": 280348.227351271, "peak_velocity": 520223.747264194, "window_hours_remaining": 20, "promotion_reason": "creator_count_emerging", "llm_classification_status": "not_needed"}, {"id": 87, "audio_title": "Nuvvena", "status": "peaked", "velocity_avg": 51227.7867341202, "peak_velocity": 88636.4678731111, "window_hours_remaining": 20, "promotion_reason": "creator_count_emerging", "llm_classification_status": "not_needed"}, {"id": 86, "audio_title": "Dooron Dooron", "status": "peaked", "velocity_avg": 47233.0618785038, "peak_velocity": 111698.082083435, "window_hours_remaining": 32, "promotion_reason": "creator_count_emerging", "llm_classification_status": "not_needed"}, {"id": 85, "audio_title": "Mahabharat Theme", "status": "peaked", "velocity_avg": 110684.242579782, "peak_velocity": 205621.213077752, "window_hours_remaining": 20, "promotion_reason": "creator_count_emerging", "llm_classification_status": "not_needed"}]}
{"ts": "2026-08-01T09:40:33.274782+00:00", "sample": "excluded_expired", "count": 5, "rows": [{"id": 67, "audio_title": "Bahut Jatate Ho Pyar Duet", "status": "expired", "velocity_avg": 244841.213650742, "peak_velocity": 244841.213650742, "window_hours_remaining": 0, "promotion_reason": "audio_use_count_rising", "llm_classification_status": "not_needed"}, {"id": 64, "audio_title": "Come Check This", "status": "expired", "velocity_avg": 22064.9937581082, "peak_velocity": 22064.9937581082, "window_hours_remaining": 0, "promotion_reason": "audio_use_count_rising", "llm_classification_status": "not_needed"}, {"id": 63, "audio_title": "Raja Tohar Ganja Pike", "status": "expired", "velocity_avg": 12507.0448853097, "peak_velocity": 12507.0448853097, "window_hours_remaining": 0, "promotion_reason": "creator_count_emerging", "llm_classification_status": "not_needed"}, {"id": 62, "audio_title": "Raavana Mavandaa", "status": "expired", "velocity_avg": 44787.7221239964, "peak_velocity": 44787.7221239964, "window_hours_remaining": 0, "promotion_reason": "audio_use_count_emerging", "llm_classification_status": "not_needed"}, {"id": 61, "audio_title": "Delhi Ke Police", "status": "expired", "velocity_avg": 40104.8828486985, "peak_velocity": 40104.8828486985, "window_hours_remaining": 0, "promotion_reason": "audio_use_count_emerging", "llm_classification_status": "not_needed"}]}
{"ts": "2026-08-01T09:40:33.274782+00:00", "sample": "excluded_llm_pending", "count": 3, "rows": [{"id": 14, "audio_title": "Dead Fresh", "status": "expired", "llm_classification_status": "skipped_local_fallback"}, {"id": 13, "audio_title": "Mujhko Barsaat Bana Lo", "status": "expired", "llm_classification_status": "skipped_local_fallback"}, {"id": 12, "audio_title": "Y Que Fue?", "status": "expired", "llm_classification_status": "skipped_local_fallback"}]}
```

### “Same window but did not make it to the frontend”

I could not prove a row “scraped in the same window” for every excluded row from only the current live tables because the scrape window boundaries are not stored as a single audit table. What I could verify is that the rows above were created in the same broad active cohort as the current feed rows, and they were excluded by lifecycle status, not by frontend rendering bugs.

### Silent failures / bugs

I did not find a live row that obviously failed silently during classification in the current active set. The closest visible issue is not silent failure but a logic/data-contract mismatch:

- the frontend only accepts `completed` or `not_needed`
- three expired rows still carry `llm_classification_status = skipped_local_fallback`

Those rows are excluded, but the status means the model fallback path happened upstream rather than a clean deterministic completion.

## 3) Pipeline trace

### Actual code path

The current detection path is in:

- [backend/cron_job.py](../backend/cron_job.py)
- [backend/trend_engine.py](../backend/trend_engine.py)
- [backend/trend_refresher.py](../backend/trend_refresher.py)

The important live logic in `backend/trend_engine.py` is:

```python
EMERGING_USE_THRESHOLD = 150000
RISING_USE_THRESHOLD = 800000

if max_use_count >= RISING_USE_THRESHOLD:
    initial_status = "rising"
    promotion_trigger = "audio_use_count_rising"
elif creator_count >= 3 and creator_velocity > 0:
    initial_status = "rising"
    promotion_trigger = "creator_count_rising"
elif max_use_count >= EMERGING_USE_THRESHOLD:
    initial_status = "emerging"
    promotion_trigger = "audio_use_count_emerging"
elif creator_count >= 2 and len(group_reels) >= 2:
    initial_status = "emerging"
    promotion_trigger = "creator_count_emerging"
```

and the window/stability logic in `backend/trend_refresher.py` is:

```python
if age_hours >= min_visible_hours or window_hours <= 0:
    status = "expired"
elif current_status == "emerging":
    if persisted_enough and qualifies_by_creator:
        status = "rising"
    elif velocity_only_persisted and creator_count < 3 and velocity_snapshot_ok:
        status = "rising"
    elif persisted_enough and qualifies_by_creator and velocity_snapshot_ok:
        status = "rising"
    else:
        status = "emerging"
else:
    status = "rising"
```

The frontend query logic is:

```ts
fetchTrends(language, sortMode, selectedNiche) -> /api/trends
fetchEmergingTrends(language) -> /api/trends/emerging
```

### Most recent full pipeline run I could verify

The latest full detection run I found in `trend_engine.log` is `2026-07-29 18:06:03` through `18:24:56`, which is the run that produced the current live set.

Key trace lines:

```text
2026-07-29 18:06:03,593 - INFO - Audio grouping: special-cased 968 original-audio reels and excluded 117 unidentifiable reels. 1570 reels proceeded to grouping. Grouped into 1472 unique audio combinations.
2026-07-29 18:09:03,684 - INFO - Confirmed 29 new trends for Groq classification
2026-07-29 18:09:03,685 - INFO - Selected top 7 trends for classification
2026-07-29 18:10:15,831 - INFO - Deterministic trend classification completed for 7/7 trends.
2026-07-29 18:10:20,269 - INFO - Saved 'Yeh Vaada Raha (Tu Tu Hai Wahi / From “Yeh Vaada Raha”)' as rising (id=29)
2026-07-29 18:10:23,363 - INFO - Saved 'Mix: dontakswhyy • Original audio | narendramodi • Original Audio' as emerging (id=30)
2026-07-29 18:10:27,286 - INFO - Saved 'Instagram Pe' as emerging (id=31)
2026-07-29 18:10:30,455 - INFO - Saved 'Pavazha Malli' as emerging (id=32)
2026-07-29 18:10:33,634 - INFO - Saved 'Abhi Na Jao Chhod Kar - Film Version 2 (From "Rocky Aur Rani Kii Prem Kahaani")' as emerging (id=33)
2026-07-29 18:10:36,931 - INFO - Saved 'Gurupurnima' as emerging (id=34)
2026-07-29 18:10:40,574 - INFO - Saved 'Satte Era Satte' as emerging (id=35)
2026-07-29 18:20:21,141 - INFO - Audio grouping: special-cased 968 original-audio reels and excluded 117 unidentifiable reels. 1570 reels proceeded to grouping. Grouped into 1472 unique audio combinations.
2026-07-29 18:23:18,589 - INFO - Confirmed 22 new trends for Groq classification
2026-07-29 18:23:18,589 - INFO - Selected top 7 trends for classification
2026-07-29 18:24:30,794 - INFO - Deterministic trend classification completed for 7/7 trends.
2026-07-29 18:24:34,382 - INFO - Saved 'X-COOL! (Slowed)' as emerging (id=36)
2026-07-29 18:24:37,441 - INFO - Saved 'Dilan Teer Bija' as emerging (id=37)
2026-07-29 18:24:40,419 - INFO - Saved 'Tain Tain To To' as rising (id=38)
2026-07-29 18:24:44,399 - INFO - Saved 'Biwi No. 1' as emerging (id=39)
2026-07-29 18:24:47,526 - INFO - Saved 'Serve' as emerging (id=40)
2026-07-29 18:24:50,516 - INFO - Saved 'Kaho Na Kaho' as rising (id=41)
2026-07-29 18:24:54,877 - INFO - Saved 'Nazra Ke Teer' as rising (id=42)
```

### Stage-by-stage counts I can verify from code + logs

| Stage | Entered | Exited | Dropped |
| --- | --- | --- | --- |
| Scrape grouping input | 1,570 reels proceeded to grouping | 1,472 unique audio combinations | 117 unidentifiable reels + 968 original-audio reels were special-cased/excluded in that run |
| Groq classification candidates | 29 confirmed | 7 selected top | 22 not sent onward |
| Deterministic classification | 7 | 7 | 0 |
| Save to `trends` | 7 | 7 saved rows are logged | 0 logged save failures in that run |

### Current API-side frontend filter

The current frontend doesn’t run a client-side filter beyond search and language/niche state. The actual exclusion point is the backend SQL query:

```python
supabase.table("trends").select("*").eq("status", "rising").in_("llm_classification_status", ["completed", "not_needed"])
supabase.table("trends").select("*").eq("status", "emerging").in_("llm_classification_status", ["completed", "not_needed"])
```

## 4) Sanity flags

### Flag 1: `India` tab is not “India-only”

Live rows in the India tab include:

- `X-COOL! (Slowed)` with `trend_origin=unknown`
- `Rang Jo Lagyo` style rows in the broader cohort show strong velocity but the region is still decided by lifecycle status, not a geographic check in the visible frontend

The visible region label is driven by tab choice, not by a separate geo-pure India dataset.

### Flag 2: Promotion reason is not always aligned with final status

Some rows were created with `promotion_reason=creator_count_emerging` but later moved to `peaked` or `expired`. That is normal lifecycle progression, but it means the creation reason is not the current reason they are still visible or not.

### Flag 3: Some current rows have `opportunity_score=0`

Example live row:

- `X-COOL! (Slowed)` has `opportunity_score=0`

That stands out because it is still actively shown in India despite the opportunity score collapsing to zero. It looks like a scoring artifact worth checking, not a frontend filter issue.

### Flag 4: `skipped_local_fallback` still exists in live data

These rows are not visible now, but they prove the pipeline sometimes bypassed the normal deterministic path and had to use a local fallback:

- `Dead Fresh`
- `Mujhko Barsaat Bana Lo`
- `Y Que Fue?`

### Flag 5: `trend_origin` is still under-classified

The live status mix includes many `unknown` or India-default rows. In the current active set, `trend_origin` is dominated by `IN` or `unknown`, and the frontend is not applying an independent region classifier.

### Flag 6: No live evidence of silent row loss in the current active set

I did not find a row that appears in the live tables but is silently missing from both tabs while still satisfying the backend filters. The main exclusions are explainable by status and classification state.

## 5) Live evidence summary

Current active rows in the frontend:

- India: 9
- Emerging: 19
- Total active: 28

Current live status distribution in `trends`:

- `emerging|not_needed`: 19
- `rising|not_needed`: 8
- `rising|completed`: 1
- `peaked|not_needed`: 27
- `peaked|completed`: 8
- `expired|not_needed`: 12
- `expired|completed`: 16
- `expired|skipped_local_fallback`: 3

If you want, I can turn this into a stricter row-by-row diff next: current live feed rows vs every excluded row in the same chronological cohort, with a compact CSV-style appendix.

## References

- [frontend/src/routes/index.tsx](../frontend/src/routes/index.tsx)
- [frontend/src/lib/api.ts](../frontend/src/lib/api.ts)
- [backend/api.py](../backend/api.py)
- [backend/trend_engine.py](../backend/trend_engine.py)
- [backend/trend_refresher.py](../backend/trend_refresher.py)
- [trend_engine.log](../trend_engine.log)
- [trend_refresher.log](../trend_refresher.log)
- [scratch/audit_query.py](../scratch/audit_query.py)

