-- Create calls table
CREATE TABLE IF NOT EXISTS calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    vendor_id UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    twilio_call_sid VARCHAR(255),
    status VARCHAR(50) DEFAULT 'initiated' CHECK (status IN ('initiated', 'connected', 'in_progress', 'completed', 'failed', 'no_answer')),
    duration_seconds INT DEFAULT 0,
    initial_ask FLOAT,
    final_offer FLOAT,
    outcome VARCHAR(50) CHECK (outcome IS NULL OR outcome IN ('agreed', 'rejected', 'no_answer', 'fraud_detected', 'vendor_unavailable')),
    recording_url TEXT,
    transcript JSONB DEFAULT '[]',
    safety_flags TEXT[] DEFAULT ARRAY[]::TEXT[],
    negotiation_summary JSONB DEFAULT '{}',
    call_started_at TIMESTAMP,
    call_ended_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_calls_trip_id ON calls(trip_id);
CREATE INDEX IF NOT EXISTS idx_calls_vendor_id ON calls(vendor_id);
CREATE INDEX IF NOT EXISTS idx_calls_status ON calls(status);
CREATE INDEX IF NOT EXISTS idx_calls_outcome ON calls(outcome);
CREATE INDEX IF NOT EXISTS idx_calls_created_at ON calls(created_at);
CREATE INDEX IF NOT EXISTS idx_calls_trip_vendor ON calls(trip_id, vendor_id);

-- Enable RLS
ALTER TABLE calls ENABLE ROW LEVEL SECURITY;
