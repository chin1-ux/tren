-- Phase 3: Supabase RLS Policies with Security-Definer Functions
-- This script replaces the temporary service-role-only policies with proper admin-bypass policies
-- Execute in Supabase SQL Editor after review

-- ============================================
-- 1. Create security-definer function to check user role
-- ============================================
CREATE OR REPLACE FUNCTION is_user_admin(user_email TEXT)
RETURNS BOOLEAN
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM users 
        WHERE email = user_email AND role = 'admin'
    );
END;
$$;

-- ============================================
-- 2. Create security-definer function to get user ID from email
-- ============================================
CREATE OR REPLACE FUNCTION get_user_id_from_email(user_email TEXT)
RETURNS BIGINT
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN (
        SELECT id FROM users 
        WHERE email = user_email 
        LIMIT 1
    );
END;
$$;

-- ============================================
-- 3. Drop temporary service-role policies
-- ============================================
DROP POLICY IF EXISTS "Service role can manage admin_actions" ON admin_actions;
DROP POLICY IF EXISTS "Service role can manage plan_overrides" ON plan_overrides;

-- ============================================
-- 4. Create admin-bypass policies for admin_actions
-- ============================================
-- Admins can read all audit logs
CREATE POLICY "Admins can read all audit logs" ON admin_actions
    FOR SELECT
    USING (is_user_admin(auth.jwt() ->> 'email'));

-- Users can read audit logs where they are the target
CREATE POLICY "Users can read their own audit logs" ON admin_actions
    FOR SELECT
    USING (
        target_user_id = get_user_id_from_email(auth.jwt() ->> 'email')
    );

-- Service role can insert audit logs (for backend API)
CREATE POLICY "Service role can insert audit logs" ON admin_actions
    FOR INSERT
    WITH CHECK (auth.role() = 'service_role');

-- Service role can update/delete audit logs (for cleanup)
CREATE POLICY "Service role can manage audit logs" ON admin_actions
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================
-- 5. Create admin-bypass policies for plan_overrides
-- ============================================
-- Admins can read all plan overrides
CREATE POLICY "Admins can read all plan overrides" ON plan_overrides
    FOR SELECT
    USING (is_user_admin(auth.jwt() ->> 'email'));

-- Users can read their own plan overrides
CREATE POLICY "Users can read their own plan overrides" ON plan_overrides
    FOR SELECT
    USING (
        user_id = get_user_id_from_email(auth.jwt() ->> 'email')
    );

-- Service role can manage plan overrides (for backend API)
CREATE POLICY "Service role can manage plan overrides" ON plan_overrides
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================
-- 6. Create admin-bypass policy for users table
-- ============================================
-- Admins can read all users
CREATE POLICY "Admins can read all users" ON users
    FOR SELECT
    USING (is_user_admin(auth.jwt() ->> 'email'));

-- Admins can update user status and plan
CREATE POLICY "Admins can update users" ON users
    FOR UPDATE
    USING (is_user_admin(auth.jwt() ->> 'email'));

-- Users can read their own data
CREATE POLICY "Users can read own data" ON users
    FOR SELECT
    USING (
        email = auth.jwt() ->> 'email'
    );

-- ============================================
-- 7. Verification queries
-- ============================================
-- Verify security-definer functions exist
SELECT routine_name, security_definer 
FROM information_schema.routines 
WHERE routine_name IN ('is_user_admin', 'get_user_id_from_email');

-- Verify RLS policies on admin_actions
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename = 'admin_actions';

-- Verify RLS policies on plan_overrides
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename = 'plan_overrides';

-- Verify RLS policies on users
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename = 'users' AND policyname LIKE '%Admin%';
