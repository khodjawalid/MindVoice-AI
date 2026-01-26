-- Daily video inference table
-- Stores one video emotion analysis per day (instead of per-tag)

CREATE TABLE IF NOT EXISTS daily_video_inferences (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  record_date DATE NOT NULL UNIQUE,
  predicted_emotion TEXT,
  pred_confidence FLOAT,
  emotion_probabilities JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for quick date lookups
CREATE INDEX IF NOT EXISTS idx_daily_video_inferences_date
ON daily_video_inferences(record_date);
