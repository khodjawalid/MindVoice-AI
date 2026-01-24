-- Supabase Tables for Aggregated Biometric Signals
-- Run this SQL in the Supabase SQL Editor

-- Table EDA Aggregated (per-minute)
CREATE TABLE IF NOT EXISTS eda_aggregated (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_date DATE NOT NULL,              -- Ex: 2026-01-22
    datetime_utc TIMESTAMPTZ NOT NULL,
    eda_mean DOUBLE PRECISION,
    eda_std DOUBLE PRECISION,
    eda_min DOUBLE PRECISION,
    eda_max DOUBLE PRECISION,
    sample_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table HR Aggregated (per-minute)
CREATE TABLE IF NOT EXISTS hr_aggregated (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_date DATE NOT NULL,              -- Ex: 2026-01-22
    datetime_utc TIMESTAMPTZ NOT NULL,
    hr_mean DOUBLE PRECISION,
    hr_std DOUBLE PRECISION,
    hr_min DOUBLE PRECISION,
    hr_max DOUBLE PRECISION,
    sample_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table Tags (with review fields for wellness workflow)
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_date DATE NOT NULL,              -- Ex: 2026-01-22
    timestamp DOUBLE PRECISION NOT NULL,
    datetime_utc TIMESTAMPTZ NOT NULL,
    -- Review fields
    emotion_label TEXT,                     -- e.g., "Happy", "Sad", "Anxious"
    stress_level INTEGER CHECK (stress_level >= 1 AND stress_level <= 10),
    video_url TEXT,
    reviewed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Migration: Add review columns to existing tags table
ALTER TABLE tags ADD COLUMN IF NOT EXISTS emotion_label TEXT;
ALTER TABLE tags ADD COLUMN IF NOT EXISTS stress_level INTEGER CHECK (stress_level >= 1 AND stress_level <= 10);
ALTER TABLE tags ADD COLUMN IF NOT EXISTS video_url TEXT;
ALTER TABLE tags ADD COLUMN IF NOT EXISTS reviewed BOOLEAN DEFAULT FALSE;

-- Indexes for queries by date (essential for filtering by day/week)
CREATE INDEX IF NOT EXISTS idx_eda_date ON eda_aggregated(record_date);
CREATE INDEX IF NOT EXISTS idx_hr_date ON hr_aggregated(record_date);
CREATE INDEX IF NOT EXISTS idx_tags_date ON tags(record_date);

-- Example query for a week of data:
-- SELECT * FROM eda_aggregated
-- WHERE record_date BETWEEN '2026-01-16' AND '2026-01-22'
-- ORDER BY datetime_utc;
