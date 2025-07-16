DROP FUNCTION IF EXISTS get_valid_stock_codes();
CREATE OR REPLACE FUNCTION public.get_valid_stock_codes()
RETURNS TABLE(stock_code VARCHAR(10))  -- ✅ Match actual column type
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT s.stock_code
    FROM api_stock s
    INNER JOIN api_daily_stock_data d ON s.id = d.stock_id
    ORDER BY s.stock_code;
END;
$$;
