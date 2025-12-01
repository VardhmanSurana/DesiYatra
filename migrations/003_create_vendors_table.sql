-- Create vendors table
CREATE TABLE IF NOT EXISTS vendors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255),
    category VARCHAR(50) NOT NULL CHECK (category IN ('taxi', 'homestay', 'guide', 'activity')),
    location VARCHAR(255),
    source VARCHAR(50) NOT NULL,
    trust_score FLOAT DEFAULT 0.7 CHECK (trust_score >= 0 AND trust_score <= 1),
    total_calls_made INT DEFAULT 0,
    successful_deals_count INT DEFAULT 0,
    average_discount_percentage FLOAT DEFAULT 0,
    is_blacklisted BOOLEAN DEFAULT FALSE,
    blacklist_reason TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_vendors_phone ON vendors(phone_number);
CREATE INDEX IF NOT EXISTS idx_vendors_category ON vendors(category);
CREATE INDEX IF NOT EXISTS idx_vendors_location ON vendors(location);
CREATE INDEX IF NOT EXISTS idx_vendors_trust_score ON vendors(trust_score);
CREATE INDEX IF NOT EXISTS idx_vendors_is_blacklisted ON vendors(is_blacklisted);
CREATE INDEX IF NOT EXISTS idx_vendors_category_location ON vendors(category, location);

-- Enable RLS
ALTER TABLE vendors ENABLE ROW LEVEL SECURITY;
