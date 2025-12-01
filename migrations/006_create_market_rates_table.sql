-- Create market_rates table for price intelligence
CREATE TABLE IF NOT EXISTS market_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(50) NOT NULL CHECK (category IN ('taxi', 'homestay', 'guide', 'activity')),
    location VARCHAR(255) NOT NULL,
    item_description VARCHAR(255) NOT NULL,
    local_rate FLOAT NOT NULL,
    tourist_rate FLOAT NOT NULL,
    source VARCHAR(100),
    valid_from DATE DEFAULT CURRENT_DATE,
    valid_until DATE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_market_rates_category_location ON market_rates(category, location);
CREATE INDEX IF NOT EXISTS idx_market_rates_location ON market_rates(location);
CREATE INDEX IF NOT EXISTS idx_market_rates_valid_dates ON market_rates(valid_from, valid_until);
CREATE INDEX IF NOT EXISTS idx_market_rates_category ON market_rates(category);

-- Enable RLS
ALTER TABLE market_rates ENABLE ROW LEVEL SECURITY;
