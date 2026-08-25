-- Supabase Migration Script for Phone Verification
-- Execute these SQL statements in your Supabase SQL Editor

-- 1. Create phone_verifications table
CREATE TABLE IF NOT EXISTS phone_verifications (
    id BIGSERIAL PRIMARY KEY,
    phone_number TEXT UNIQUE NOT NULL,
    verification_code TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add last_otp_sent_at explicitly in case table already existed
ALTER TABLE phone_verifications ADD COLUMN IF NOT EXISTS last_otp_sent_at TIMESTAMP WITH TIME ZONE;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_phone_verifications_phone ON phone_verifications(phone_number);
CREATE INDEX IF NOT EXISTS idx_phone_verifications_expires ON phone_verifications(expires_at);

-- 2. Enable RLS on phone_verifications
ALTER TABLE phone_verifications ENABLE ROW LEVEL SECURITY;

-- Allow insert/select from service role only (since it's managed via backend API)
CREATE POLICY ""Service Role Full Access"" ON phone_verifications
    USING (true);

-- 3. Add phone_number and phone_verified columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT FALSE;

-- Ensure constraints if needed
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_phone_number_key;
ALTER TABLE users ADD CONSTRAINT users_phone_number_key UNIQUE (phone_number);
