DROP FUNCTION IF EXISTS add_single_weekly_expiry(
    input_stock_code VARCHAR,
    input_expiry_date DATE,
    input_expiry_month VARCHAR);
CREATE OR REPLACE FUNCTION add_single_weekly_expiry(
    input_stock_code VARCHAR,
    input_expiry_date DATE,
    input_expiry_month VARCHAR
)
RETURNS VOID AS $$
DECLARE
    v_stock_id INTEGER;
BEGIN
    SELECT id INTO v_stock_id
    FROM api_stock
    WHERE stock_code = input_stock_code
    LIMIT 1;

    IF v_stock_id IS NOT NULL THEN
        INSERT INTO api_expiry_stock (stock_id, month, expiry_date)
        SELECT v_stock_id, input_expiry_month, input_expiry_date
        WHERE NOT EXISTS (
            SELECT 1 FROM api_expiry_stock
            WHERE stock_id = v_stock_id
              AND month = input_expiry_month
              AND expiry_date = input_expiry_date
        );
    END IF;
END;
$$ LANGUAGE plpgsql;