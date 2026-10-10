-- Migration 016: Coverage Report Table (Order 70 Part 6.1)
-- Additive, RLS enabled, zero policies

CREATE TABLE IF NOT EXISTS coverage_report (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    week_start date,
    metric text,
    value double precision,
    n int,
    note text,
    created_at timestamptz DEFAULT now()
);

ALTER TABLE coverage_report ENABLE ROW LEVEL SECURITY;
