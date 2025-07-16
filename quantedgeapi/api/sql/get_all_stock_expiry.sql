CREATE OR REPLACE FUNCTION get_expiry_stocks_with_stock_info()
RETURNS TABLE (
    expiry_id BIGINT,
    stock_id BIGINT,
    month VARCHAR,
    expiry_date DATE,
    stock_code VARCHAR,
    stock_name VARCHAR,
    lot_size INTEGER,
    exchange_code VARCHAR,
    stock_type VARCHAR,
    fno_exchange_code VARCHAR
) AS $$
BEGIN
    RETURN QUERY 
    SELECT 
        es.id AS expiry_id,
        s.id AS stock_id,
        es.month,
        es.expiry_date,
        s.stock_code,
        s.stock_name,
        s.lot_size,
        s.exchange_code,
        s.stock_type,
        s.fno_exchange_code
    FROM api_expiry_stock es
    JOIN api_stock s ON es.stock_id = s.id;
END;
$$ LANGUAGE plpgsql;
DROP FUNCTION IF EXISTS get_stock_expiry_id(VARCHAR);
CREATE OR REPLACE FUNCTION get_expiry_stock_id(p_stock_code VARCHAR, p_expiry_date DATE)
RETURNS INT AS $$
DECLARE
    v_expiry_stock_id INT;
BEGIN
    -- Fetch expiry stock ID by joining with api_stock for stock_code
    SELECT es.id
    INTO v_expiry_stock_id
    FROM api_expiry_stock es
    JOIN api_stock s ON es.stock_id = s.id
    WHERE s.stock_code = p_stock_code
      AND es.expiry_date = p_expiry_date
    LIMIT 1;

    RETURN v_expiry_stock_id;
END;
$$ LANGUAGE plpgsql;