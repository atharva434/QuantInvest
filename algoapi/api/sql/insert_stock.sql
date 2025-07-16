CREATE OR REPLACE FUNCTION insert_stock(
    p_stock_code VARCHAR,
    p_stock_name VARCHAR,
    p_lot_size INTEGER,
    p_exchange_code VARCHAR,
    p_stock_type VARCHAR,
    p_fno_exchange_code VARCHAR
) RETURNS VOID AS $$
BEGIN
    INSERT INTO api_stock (
        stock_code, stock_name, lot_size, exchange_code, stock_type, fno_exchange_code
    ) VALUES (
        p_stock_code, p_stock_name, p_lot_size, p_exchange_code, p_stock_type, p_fno_exchange_code
    );
END;
$$ LANGUAGE plpgsql;