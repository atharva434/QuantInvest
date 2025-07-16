CREATE OR REPLACE FUNCTION update_stock(
    p_id INTEGER,
    p_stock_code VARCHAR,
    p_stock_name VARCHAR,
    p_lot_size INTEGER,
    p_exchange_code VARCHAR,
    p_stock_type VARCHAR,
    p_fno_exchange_code VARCHAR
)
RETURNS VOID AS $$
BEGIN
    UPDATE api_stock
    SET
        stock_code = p_stock_code,
        stock_name = p_stock_name,
        lot_size = p_lot_size,
        exchange_code = p_exchange_code,
        stock_type = p_stock_type,
        fno_exchange_code = p_fno_exchange_code
    WHERE id = p_id;
END;
$$ LANGUAGE plpgsql;