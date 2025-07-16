CREATE OR REPLACE FUNCTION get_min_max_for_stock_code(p_stock_code TEXT)
RETURNS TABLE (
    id BIGINT,
    stock_code VARCHAR(10),
    min_date DATE,
    max_date DATE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id,
        s.stock_code,
        MIN(d.date) AS min_date,
        MAX(d.date) AS max_date
    FROM api_stock s
    INNER JOIN api_daily_stock_data d ON s.id = d.stock_id
    WHERE s.stock_code = p_stock_code
    GROUP BY s.id, s.stock_code;
END;
$$;


