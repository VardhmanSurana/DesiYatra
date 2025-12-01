-- Create trips table
CREATE TABLE IF NOT EXISTS trips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    destination VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    party_size INT NOT NULL CHECK (party_size > 0),
    budget_min FLOAT NOT NULL CHECK (budget_min > 0),
    budget_max FLOAT NOT NULL CHECK (budget_max >= budget_min),
    budget_stretch FLOAT NOT NULL CHECK (budget_stretch >= budget_max),
    services TEXT[] DEFAULT ARRAY['taxi'] CHECK (services && ARRAY['taxi', 'homestay', 'guide', 'activity']),
    preferences JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'planning' CHECK (status IN ('planning', 'scouting', 'vetting', 'negotiating', 'confirming', 'complete', 'failed')),
    failure_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_trips_user_id ON trips(user_id);
CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);
CREATE INDEX IF NOT EXISTS idx_trips_destination ON trips(destination);
CREATE INDEX IF NOT EXISTS idx_trips_created_at ON trips(created_at);

-- Enable RLS
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
