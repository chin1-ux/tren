-- Phase 1 Schema Migration: Admin/Role System Rebuild
-- This script adds role column to users table and creates new admin tables
-- Execute in Supabase SQL Editor after review

-- ============================================
-- 1. Add role column to users table (non-destructive)
-- ============================================
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user';

-- Add check constraint to ensure only valid role values
ALTER TABLE users 
ADD CONSTRAINT users_role_check 
CHECK (role IN ('user', 'admin'));

-- ============================================
-- 2. Create admin_actions audit log table
-- ============================================
CREATE TABLE IF NOT EXISTS admin_actions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    admin_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    target_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for audit log queries
CREATE INDEX IF NOT EXISTS idx_admin_actions_admin_id ON admin_actions(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_actions_target_user_id ON admin_actions(target_user_id);
CREATE INDEX IF NOT EXISTS idx_admin_actions_created_at ON admin_actions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_actions_action ON admin_actions(action);

-- ============================================
-- 3. Create plan_overrides table for manual plan grants
-- ============================================
CREATE TABLE IF NOT EXISTS plan_overrides (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    tier TEXT NOT NULL, -- 'free', 'creator', 'agency'
    granted_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    expires_at TIMESTAMPTZ, -- NULL means permanent
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for plan override queries
CREATE INDEX IF NOT EXISTS idx_plan_overrides_user_id ON plan_overrides(user_id);
CREATE INDEX IF NOT EXISTS idx_plan_overrides_expires_at ON plan_overrides(expires_at);
CREATE INDEX IF NOT EXISTS idx_plan_overrides_tier ON plan_overrides(tier);

-- Add check constraint for valid tier values
ALTER TABLE plan_overrides 
ADD CONSTRAINT plan_overrides_tier_check 
CHECK (tier IN ('free', 'creator', 'agency'));

-- ============================================
-- 4. Handle existing broken admin tables (rename for safety)
-- ============================================
-- Rename old admin tables instead of dropping to allow rollback if needed
ALTER TABLE IF EXISTS admin_users RENAME TO admin_users_deprecated_20240813;
ALTER TABLE IF EXISTS admin_audit_log RENAME TO admin_audit_log_deprecated_20240813;
ALTER TABLE IF EXISTS admin_audit_log_enhanced RENAME TO admin_audit_log_enhanced_deprecated_20240813;

-- ============================================
-- 5. Enable RLS on new tables
-- ============================================
ALTER TABLE admin_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE plan_overrides ENABLE ROW LEVEL SECURITY;

-- ============================================
-- 6. Create secure RLS policies (service role only)
-- ============================================
-- Service role only policies - will be replaced with proper security-definer policies in Phase 3
CREATE POLICY "Service role can manage admin_actions" ON admin_actions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage plan_overrides" ON plan_overrides
    FOR ALL USING (auth.role() = 'service_role');

-- ============================================
-- 7. Migration verification queries
-- ============================================
-- Verify role column added to users table
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'role';

-- Verify admin_actions table created
SELECT table_name 
FROM information_schema.tables 
WHERE table_name = 'admin_actions';

-- Verify plan_overrides table created  
SELECT table_name 
FROM information_schema.tables 
WHERE table_name = 'plan_overrides';

-- Verify old tables renamed
SELECT table_name 
FROM information_schema.tables 
WHERE table_name LIKE '%deprecated%';
