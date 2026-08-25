-- Supabase Migration Script for Admin System (Clean Version)
-- Execute these SQL statements in your Supabase SQL Editor
-- This version handles existing policies by dropping them first

-- 1. Drop existing policies if they exist
DROP POLICY IF EXISTS "Super admins can manage admin users" ON admin_users;
DROP POLICY IF EXISTS "Admins can read audit logs" ON admin_audit_log_enhanced;
DROP POLICY IF EXISTS "System can insert audit logs" ON admin_audit_log_enhanced;

-- 2. Disable RLS temporarily to make changes
ALTER TABLE admin_users DISABLE ROW LEVEL SECURITY;
ALTER TABLE admin_audit_log_enhanced DISABLE ROW LEVEL SECURITY;

-- 3. Create admin_users table (or recreate it)
DROP TABLE IF EXISTS admin_users CASCADE;
CREATE TABLE admin_users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('super_admin', 'admin', 'read_only')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ
);

-- 4. Create enhanced admin audit log table (or recreate it)
DROP TABLE IF EXISTS admin_audit_log_enhanced CASCADE;
CREATE TABLE admin_audit_log_enhanced (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    admin_email TEXT NOT NULL,
    action TEXT NOT NULL,
    target_user_email TEXT,
    details JSONB,
    ip_address TEXT,
    user_agent TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Create indexes for faster queries
CREATE INDEX idx_admin_audit_log_enhanced_admin_email ON admin_audit_log_enhanced(admin_email);
CREATE INDEX idx_admin_audit_log_enhanced_timestamp ON admin_audit_log_enhanced(timestamp);
CREATE INDEX idx_admin_audit_log_enhanced_action ON admin_audit_log_enhanced(action);

-- 6. Add version field to plan_features table for optimistic locking
ALTER TABLE plan_features 
ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;

-- 7. Create initial admin user
-- IMPORTANT: Change this password immediately after first login!
INSERT INTO admin_users (email, password_hash, role, created_at)
VALUES ('chinmay.feb03@gmail.com', '$2b$12$7JZNe0djt51ugVjbExFVduu6EY4et/xunOMHTB9ZbB91.37Y9MZHu', 'super_admin', NOW())
ON CONFLICT (email) DO NOTHING;

-- 8. Enable Row Level Security (RLS) for admin tables
ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_audit_log_enhanced ENABLE ROW LEVEL SECURITY;

-- 9. Create RLS policies for admin_users
-- Only super_admins can manage admin users
CREATE POLICY "Super admins can manage admin users" ON admin_users
    FOR ALL USING (
        auth.jwt() ->> 'email' IN (
            SELECT email FROM admin_users WHERE role = 'super_admin'
        )
    );

-- 10. Create RLS policies for admin_audit_log_enhanced
-- Only admins can read audit logs
CREATE POLICY "Admins can read audit logs" ON admin_audit_log_enhanced
    FOR SELECT USING (
        auth.jwt() ->> 'email' IN (
            SELECT email FROM admin_users WHERE role IN ('super_admin', 'admin')
        )
    );

-- Only the system can insert audit logs (via API)
CREATE POLICY "System can insert audit logs" ON admin_audit_log_enhanced
    FOR INSERT WITH CHECK (true);

-- 11. Grant necessary permissions
GRANT ALL ON admin_users TO authenticated;
GRANT ALL ON admin_audit_log_enhanced TO authenticated;

-- IMPORTANT: Set these environment variables in your deployment:
-- JWT_SECRET_KEY=9xK2mN8pQ4vR7sT1wY5zA3bC6dE9fG2hJ5kM8nP1qS4tV7wX0zB3cF6iJ9lN2oP5rS8uV1yZ4
-- INITIAL_ADMIN_EMAIL=chinmay.feb03@gmail.com
-- INITIAL_ADMIN_PASSWORD=TrendropSecure2026!Admin