CREATE OR REPLACE PROCEDURE insert_daily_stock_data(
    p_stock_code TEXT,
    p_stock_id BIGINT,
    p_date DATE,
    p_open NUMERIC,
    p_high NUMERIC,
    p_low NUMERIC,
    p_close NUMERIC,
    p_volume BIGINT,
    p_expiry DATE
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Skip if duplicate exists
    IF EXISTS (
        SELECT 1 FROM api_daily_stock_data
        WHERE stock_code = p_stock_code AND date = p_date
    ) THEN
        RAISE NOTICE '⚠️ Skipped insert: % already exists on %', p_stock_code, p_date;
        RETURN;
    END IF;

    -- Skip if market was closed (all values 0)
    IF p_open = 0 AND p_high = 0 AND p_low = 0 AND p_close = 0 AND p_volume = 0 THEN
        RAISE NOTICE 'ℹ️ Skipped insert: % on % has all zero market data', p_stock_code, p_date;
        RETURN;
    END IF;

    -- Insert record
    INSERT INTO api_daily_stock_data (
        stock_code, stock_id, date, open, high, low, close, volume, expiry
    )
    VALUES (
        p_stock_code, p_stock_id, p_date, p_open, p_high, p_low, p_close, p_volume, p_expiry
    );
END;
$$;

