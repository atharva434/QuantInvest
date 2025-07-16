CREATE OR REPLACE PROCEDURE update_expiry_stock(
    p_id INTEGER,
    p_stock_id INTEGER,
    p_month VARCHAR,
    p_expiry_date DATE
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE api_expiry_stock
    SET stock_id = p_stock_id,
        month = p_month,
        expiry_date = p_expiry_date
    WHERE id = p_id;
END;
$$;