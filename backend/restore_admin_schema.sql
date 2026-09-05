-- Phase 1: Restore admin schema tables
-- These tables were dropped in a prior session and need to be recreated

CREATE TABLE IF NOT EXISTS admin_users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE NOT NULL,
  password_hash text NOT NULL,
  role text NOT NULL CHECK (role IN ('admin','super_admin')),
  created_at timestamptz DEFAULT now(),
  last_login timestamptz,
  failed_login_attempts int DEFAULT 0,
  locked_until timestamptz
);

CREATE TABLE IF NOT EXISTS admin_audit_log (
  id bigserial PRIMARY KEY,
  admin_email text NOT NULL,
  action text NOT NULL,
  target_user_email text,
  details jsonb,
  ip_address text,
  timestamp timestamp DEFAULT now()
);

CREATE TABLE IF NOT EXISTS admin_audit_log_enhanced (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_email text NOT NULL,
  action text NOT NULL,
  target_user_email text,
  details jsonb,
  ip_address text,
  user_agent text,
  timestamp timestamptz DEFAULT now()
);

-- Note: Admin user insertion will be done separately with bcrypt hash
