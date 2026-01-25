-- Video Inferences Table
-- Stores emotion inference results from video recordings during tag review

CREATE TABLE IF NOT EXISTS video_inferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    record_date DATE NOT NULL,
    predicted_emotion TEXT NOT NULL,
    pred_confidence DOUBLE PRECISION NOT NULL,
    emotion_probabilities JSONB NOT NULL,  -- {emotion: probability, ...}
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for querying by tag
CREATE INDEX IF NOT EXISTS idx_video_inferences_tag ON video_inferences(tag_id);

-- Index for querying by date (for dashboard)
CREATE INDEX IF NOT EXISTS idx_video_inferences_date ON video_inferences(record_date);

-- Index for querying by date and sorting by created_at
CREATE INDEX IF NOT EXISTS idx_video_inferences_date_created ON video_inferences(record_date, created_at DESC);

COMMENT ON TABLE video_inferences IS 'Stores multimodal emotion inference results from video recordings';
COMMENT ON COLUMN video_inferences.tag_id IS 'Reference to the tag this inference was recorded for';
COMMENT ON COLUMN video_inferences.predicted_emotion IS 'The dominant predicted emotion from late fusion (9 classes)';
COMMENT ON COLUMN video_inferences.pred_confidence IS 'Confidence score (0-1) for the predicted emotion';
COMMENT ON COLUMN video_inferences.emotion_probabilities IS 'JSON object with all 9 emotion probabilities';
