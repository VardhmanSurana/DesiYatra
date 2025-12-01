-- Function to get current user ID from JWT or session
CREATE OR REPLACE FUNCTION current_user_id()
RETURNS TEXT AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_user_id', true), '');
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to update vendor statistics after a call
CREATE OR REPLACE FUNCTION update_vendor_stats_after_call(
    p_vendor_id UUID,
    p_success BOOLEAN,
    p_discount_percentage FLOAT DEFAULT 0
)
RETURNS void AS $$
BEGIN
    UPDATE vendors
    SET
        total_calls_made = total_calls_made + 1,
        successful_deals_count = successful_deals_count + (CASE WHEN p_success THEN 1 ELSE 0 END),
        average_discount_percentage = (
            (average_discount_percentage * (total_calls_made - 1) + (CASE WHEN p_success THEN p_discount_percentage ELSE 0 END))
            / total_calls_made
        ),
        trust_score = CASE
            WHEN successful_deals_count = 0 THEN 0.7
            ELSE LEAST(0.95, 0.5 + (successful_deals_count::FLOAT / total_calls_made))
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_vendor_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get market rate for a service
CREATE OR REPLACE FUNCTION get_market_rate(
    p_category VARCHAR,
    p_location VARCHAR,
    p_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE(local_rate FLOAT, tourist_rate FLOAT, item_description VARCHAR) AS $$
BEGIN
    RETURN QUERY
    SELECT mr.local_rate, mr.tourist_rate, mr.item_description
    FROM market_rates mr
    WHERE mr.category = p_category
        AND mr.location ILIKE '%' || p_location || '%'
        AND mr.valid_from <= p_date
        AND (mr.valid_until IS NULL OR mr.valid_until >= p_date)
    ORDER BY mr.updated_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to get best vendors for negotiation
CREATE OR REPLACE FUNCTION get_best_vendors_for_negotiation(
    p_category VARCHAR,
    p_location VARCHAR,
    p_limit INT DEFAULT 10
)
RETURNS TABLE(
    id UUID,
    phone_number VARCHAR,
    name VARCHAR,
    trust_score FLOAT,
    total_calls_made INT,
    successful_deals_count INT,
    average_discount_percentage FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.id,
        v.phone_number,
        v.name,
        v.trust_score,
        v.total_calls_made,
        v.successful_deals_count,
        v.average_discount_percentage
    FROM vendors v
    WHERE v.category = p_category
        AND v.location ILIKE '%' || p_location || '%'
        AND v.is_blacklisted = FALSE
    ORDER BY v.trust_score DESC, v.successful_deals_count DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to update trip status
CREATE OR REPLACE FUNCTION update_trip_status(
    p_trip_id UUID,
    p_status VARCHAR,
    p_failure_reason TEXT DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    UPDATE trips
    SET
        status = p_status,
        failure_reason = p_failure_reason,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_trip_id;
END;
$$ LANGUAGE plpgsql;

-- Create function to handle updated_at automatically
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for automatic timestamp updates
DROP TRIGGER IF EXISTS users_update_timestamp ON users;
CREATE TRIGGER users_update_timestamp BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS trips_update_timestamp ON trips;
CREATE TRIGGER trips_update_timestamp BEFORE UPDATE ON trips
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS vendors_update_timestamp ON vendors;
CREATE TRIGGER vendors_update_timestamp BEFORE UPDATE ON vendors
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS calls_update_timestamp ON calls;
CREATE TRIGGER calls_update_timestamp BEFORE UPDATE ON calls
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS market_rates_update_timestamp ON market_rates;
CREATE TRIGGER market_rates_update_timestamp BEFORE UPDATE ON market_rates
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- RLS Policies for users table (defined after current_user_id function exists)
DROP POLICY IF EXISTS "Users can view their own data" ON users;
CREATE POLICY "Users can view their own data" ON users
    FOR SELECT USING (id::text = current_user_id());

DROP POLICY IF EXISTS "Users can update their own data" ON users;
CREATE POLICY "Users can update their own data" ON users
    FOR UPDATE USING (id::text = current_user_id());

-- RLS Policies for trips table
DROP POLICY IF EXISTS "Users can view their own trips" ON trips;
CREATE POLICY "Users can view their own trips" ON trips
    FOR SELECT USING (user_id::text = current_user_id());

DROP POLICY IF EXISTS "Users can update their own trips" ON trips;
CREATE POLICY "Users can update their own trips" ON trips
    FOR UPDATE USING (user_id::text = current_user_id());

DROP POLICY IF EXISTS "Users can create trips" ON trips;
CREATE POLICY "Users can create trips" ON trips
    FOR INSERT WITH CHECK (user_id::text = current_user_id());

-- RLS Policies for vendors table
DROP POLICY IF EXISTS "Everyone can view vendors" ON vendors;
CREATE POLICY "Everyone can view vendors" ON vendors
    FOR SELECT USING (true);

-- RLS Policies for calls table
DROP POLICY IF EXISTS "Users can view their call records" ON calls;
CREATE POLICY "Users can view their call records" ON calls
    FOR SELECT USING (
        trip_id IN (
            SELECT id FROM trips WHERE user_id::text = current_user_id()
        )
    );

-- RLS Policies for call_events table
DROP POLICY IF EXISTS "Users can view their call events" ON call_events;
CREATE POLICY "Users can view their call events" ON call_events
    FOR SELECT USING (
        call_id IN (
            SELECT calls.id FROM calls
            INNER JOIN trips ON calls.trip_id = trips.id
            WHERE trips.user_id::text = current_user_id()
        )
    );

-- RLS Policies for market_rates table
DROP POLICY IF EXISTS "Everyone can view market rates" ON market_rates;
CREATE POLICY "Everyone can view market rates" ON market_rates
    FOR SELECT USING (true);
