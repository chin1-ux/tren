-- Supabase Migration Script for Admin System
-- Execute these SQL statements in your Supabase SQL Editor

-- 1. Create admin_users table
CREATE TABLE IF NOT EXISTS admin_users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('super_admin', 'admin', 'read_only')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ
);

-- 2. Create enhanced admin audit log table
CREATE TABLE IF NOT EXISTS admin_audit_log_enhanced (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    admin_email TEXT NOT NULL,
    action TEXT NOT NULL,
    target_user_email TEXT,
    details JSONB,
    ip_address TEXT,
    user_agent TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_admin_audit_log_enhanced_admin_email ON admin_audit_log_enhanced(admin_email);
CREATE INDEX IF NOT EXISTS idx_admin_audit_log_enhanced_timestamp ON admin_audit_log_enhanced(timestamp);
CREATE INDEX IF NOT EXISTS idx_admin_audit_log_enhanced_action ON admin_audit_log_enhanced(action);

-- 3. Add version field to plan_features table for optimistic locking
ALTER TABLE plan_features 
ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;

-- 4. Create initial admin user
-- IMPORTANT: Change this password immediately after first login!
INSERT INTO admin_users (email, password_hash, role, created_at)
VALUES ('chinmay.feb03@gmail.com', '$2b$12$7JZNe0djt51ugVjbExFVduu6EY4et/xunOMHTB9ZbB91.37Y9MZHu', 'super_admin', NOW())
ON CONFLICT (email) DO NOTHING;

-- 5. Enable Row Level Security (RLS) for admin tables
ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_audit_log_enhanced ENABLE ROW LEVEL SECURITY;

-- 6. Create RLS policies for admin_users
-- Only super_admins can manage admin users
CREATE POLICY "Super admins can manage admin users" ON admin_users
    FOR ALL USING (
        auth.jwt() ->> 'email' IN (
            SELECT email FROM admin_users WHERE role = 'super_admin'
        )
    );

-- 7. Create RLS policies for admin_audit_log_enhanced
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

-- IMPORTANT: Set these environment variables in your deployment:
-- JWT_SECRET_KEY=your-secure-random-secret-key-here
-- INITIAL_ADMIN_EMAIL=chinmay.feb03@gmail.com
-- INITIAL_ADMIN_PASSWORD=your-secure-password-here