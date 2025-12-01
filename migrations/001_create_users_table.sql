-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255),
    preferred_language VARCHAR(20) DEFAULT 'hinglish' CHECK (preferred_language IN ('hindi', 'english', 'hinglish')),
    trust_score FLOAT DEFAULT 1.0 CHECK (trust_score >= 0 AND trust_score <= 1),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on phone_number for fast lookups
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number);

-- Create index on created_at for filtering by date
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- Enable RLS (Row Level Security)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
