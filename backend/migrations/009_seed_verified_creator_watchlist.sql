-- Migration: Seed 8 Verified Creator Watchlist accounts into creator_baselines
-- Follows DB Migration Pattern rule and Standing DB Access rule.

INSERT INTO creator_baselines (username, watchlist_tier, watchlist_status, created_at)
VALUES 
  ('daublegum', 'tier_3a_macro', 'active', NOW()),
  ('chopdaily', 'tier_3a_macro', 'active', NOW()),
  ('worldofdance', 'tier_3a_macro', 'active', NOW()),
  ('kylehanagami', 'tier_3a_macro', 'active', NOW()),
  ('mattsteffanina', 'tier_3a_macro', 'active', NOW()),
  ('shirlenequigley', 'tier_3a_macro', 'active', NOW()),
  ('teamnaach', 'tier_3a_macro', 'active', NOW()),
  ('awez_darbar', 'tier_3a_macro', 'active', NOW())
ON CONFLICT (username) 
DO UPDATE SET 
  watchlist_status = 'active',
  watchlist_tier = EXCLUDED.watchlist_tier;
