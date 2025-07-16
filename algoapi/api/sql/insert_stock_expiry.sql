CREATE OR REPLACE FUNCTION insert_expiry_stock(
    _stock_id INT,
    _month VARCHAR,
    _expiry_date DATE
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO api_expiry_stock (stock_id, month, expiry_date)
    VALUES (_stock_id, _month, _expiry_date);
END;
$$ LANGUAGE plpgsql;