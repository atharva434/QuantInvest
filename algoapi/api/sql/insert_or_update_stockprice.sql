CREATE OR REPLACE FUNCTION upsert_stock_price(
    p_stock_id INT,
    p_date VARCHAR,
    p_open FLOAT,
    p_high FLOAT,
    p_low FLOAT,
    p_close FLOAT,
    p_volume FLOAT,
    p_timestamp TIMESTAMP
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO api_stockprice (stock_id, date, open, high, low, close, volume, timestamp)
    VALUES (p_stock_id, p_date, p_open, p_high, p_low, p_close, p_volume, p_timestamp)
    ON CONFLICT (stock_id, date)
    DO UPDATE SET
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume,
        timestamp = EXCLUDED.timestamp;
END;
$$ LANGUAGE plpgsql;