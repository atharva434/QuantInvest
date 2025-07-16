CREATE OR REPLACE FUNCTION get_all_stocks()
RETURNS TABLE (
    id BIGINT,
    stock_code VARCHAR,
    stock_name VARCHAR,
    lot_size INT,
    exchange_code VARCHAR,
    stock_type VARCHAR,
    fno_exchange_code VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id,
        s.stock_code,
        s.stock_name,
        s.lot_size,
        s.exchange_code,
        s.stock_type,
        s.fno_exchange_code
    FROM api_stock s;
END;
$$ LANGUAGE plpgsql;
DROP FUNCTION IF EXISTS get_stock_info(VARCHAR);
CREATE OR REPLACE FUNCTION get_stock_info_by_id(p_id BIGINT)
RETURNS TABLE (
    id BIGINT,
    stock_code VARCHAR,
    stock_name VARCHAR,
    lot_size INT,
    exchange_code VARCHAR,
    stock_type VARCHAR,
    fno_exchange_code VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id, s.stock_code, s.stock_name, s.lot_size,
        s.exchange_code, s.stock_type, s.fno_exchange_code
    FROM api_stock s
    WHERE s.id = p_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_stock_info_by_code(p_code VARCHAR)
RETURNS TABLE (
    id BIGINT,
    stock_code VARCHAR,
    stock_name VARCHAR,
    lot_size INT,
    exchange_code VARCHAR,
    stock_type VARCHAR,
    fno_exchange_code VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id, s.stock_code, s.stock_name, s.lot_size,
        s.exchange_code, s.stock_type, s.fno_exchange_code
    FROM api_stock s
    WHERE s.stock_code = p_code;
END;
$$ LANGUAGE plpgsql;