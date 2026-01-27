-- Migration: Add Hume AI columns to daily_video_inferences
-- Run this in Supabase SQL Editor

ALTER TABLE daily_video_inferences 
ADD COLUMN IF NOT EXISTS backend TEXT DEFAULT 'local';

ALTER TABLE daily_video_inferences 
ADD COLUMN IF NOT EXISTS video_path TEXT;

ALTER TABLE daily_video_inferences 
ADD COLUMN IF NOT EXISTS raw_face_emotions JSONB;

ALTER TABLE daily_video_inferences 
ADD COLUMN IF NOT EXISTS raw_prosody_emotions JSONB;

-- Add comment
COMMENT ON COLUMN daily_video_inferences.backend IS 'Inference backend: hume or local';
COMMENT ON COLUMN daily_video_inferences.video_path IS 'Local path to saved video file';
COMMENT ON COLUMN daily_video_inferences.raw_face_emotions IS 'Raw Hume face emotions (48 dimensions)';
COMMENT ON COLUMN daily_video_inferences.raw_prosody_emotions IS 'Raw Hume prosody emotions (48 dimensions)';
