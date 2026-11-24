-- Migration / Seed Note: Multi-mode Scraper Sessions (Order 91 B1)
-- Clones existing 'instagram_primary' cookies into 'instagram_india' and 'instagram_global'
-- so each cluster operates on its own session without cross-mode collision.

INSERT INTO scraper_sessions (id, cookies, session_status, account_username, last_slid_at, last_verified_at, expires_at, metadata)
SELECT 
    'instagram_india' as id,
    cookies,
    session_status,
    account_username,
    last_slid_at,
    last_verified_at,
    expires_at,
    jsonb_set(COALESCE(metadata, '{}'::jsonb), '{mode}', '"india"')
FROM scraper_sessions
WHERE id = 'instagram_primary'
ON CONFLICT (id) DO UPDATE SET
    cookies = EXCLUDED.cookies,
    session_status = EXCLUDED.session_status,
    last_slid_at = EXCLUDED.last_slid_at;

INSERT INTO scraper_sessions (id, cookies, session_status, account_username, last_slid_at, last_verified_at, expires_at, metadata)
SELECT 
    'instagram_global' as id,
    cookies,
    session_status,
    account_username,
    last_slid_at,
    last_verified_at,
    expires_at,
    jsonb_set(COALESCE(metadata, '{}'::jsonb), '{mode}', '"global"')
FROM scraper_sessions
WHERE id = 'instagram_primary'
ON CONFLICT (id) DO UPDATE SET
    cookies = EXCLUDED.cookies,
    session_status = EXCLUDED.session_status,
    last_slid_at = EXCLUDED.last_slid_at;
