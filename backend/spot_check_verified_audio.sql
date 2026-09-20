-- ──────────────────────────────────────────────────────────────────────────────
-- Spot-check: DOM-verified audio from tonight's reel audit (Batch 1, reels 1–20)
-- Run via Supabase SQL Editor.
-- ──────────────────────────────────────────────────────────────────────────────

-- ─── Finding 1: Ryan Leslie "Addiction" ──────────────────────────────────────
-- Source: Reels #1 (@naap.04) and #17 (@skibidi_chaiiwala) both carried this
-- audio, independently. That's a cross-creator adoption signal.
-- Check if this audio is currently tracked in trends or reels:

SELECT
    'trends' AS source_table,
    id::text AS id,
    audio_title,
    audio_artist,
    status,
    velocity_avg,
    reel_count,
    created_at
FROM trends
WHERE
    (LOWER(audio_title) LIKE '%addiction%' AND LOWER(audio_title) LIKE '%ryan%')
    OR (LOWER(audio_title) LIKE '%addiction%' AND LOWER(audio_artist) LIKE '%ryan%')
    OR (LOWER(audio_artist) LIKE '%ryan leslie%')

UNION ALL

SELECT
    'reels' AS source_table,
    reel_id::text AS id,
    audio_title,
    audio_artist,
    'n/a' AS status,
    NULL::float AS velocity_avg,
    NULL::int AS reel_count,
    scraped_at AS created_at
FROM reels
WHERE
    (LOWER(audio_title) LIKE '%addiction%' AND LOWER(audio_title) LIKE '%ryan%')
    OR (LOWER(audio_title) LIKE '%addiction%' AND LOWER(audio_artist) LIKE '%ryan%')
    OR (LOWER(audio_artist) LIKE '%ryan leslie%')
ORDER BY source_table, created_at DESC;

-- Expected: If BOTH return 0 rows, this is a confirmed pipeline miss.
-- (2 independent creators using it, zero detection.)

-- ─────────────────────────────────────────────────────────────────────────────

-- ─── Finding 2: Diana Ross "Upside Down" ─────────────────────────────────────
-- Source: Reels #5 (@manuregato) and #6 (@hana_rass) — same audio AND matching
-- transition caption/hashtag pattern. Hybrid audio+format trend signal.
-- Check if this audio is currently tracked:

SELECT
    'trends' AS source_table,
    id::text AS id,
    audio_title,
    audio_artist,
    status,
    velocity_avg,
    reel_count,
    created_at
FROM trends
WHERE
    (LOWER(audio_title) LIKE '%upside down%' AND LOWER(audio_artist) LIKE '%diana%')
    OR LOWER(audio_artist) LIKE '%diana ross%'
    OR LOWER(audio_title) LIKE '%upside down%'

UNION ALL

SELECT
    'reels' AS source_table,
    reel_id::text AS id,
    audio_title,
    audio_artist,
    'n/a' AS status,
    NULL::float AS velocity_avg,
    NULL::int AS reel_count,
    scraped_at AS created_at
FROM reels
WHERE
    (LOWER(audio_title) LIKE '%upside down%' AND LOWER(audio_artist) LIKE '%diana%')
    OR LOWER(audio_artist) LIKE '%diana ross%'
    OR LOWER(audio_title) LIKE '%upside down%'
ORDER BY source_table, created_at DESC;

-- Expected: If BOTH return 0 rows, confirmed pipeline miss of a multi-creator
-- audio+format signal. Worth keeping as a regression test case.

-- ─────────────────────────────────────────────────────────────────────────────

