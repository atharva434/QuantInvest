CREATE OR REPLACE FUNCTION public.fetch_historical_stock_data_range(
    in_stock_code TEXT,
    in_start_date DATE,
    in_end_date DATE
)
RETURNS TABLE (
    date DATE,
    open NUMERIC,
    close NUMERIC,
    expiry DATE,
    high NUMERIC,
    low NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.date,
        d.open,
        d.close,
        d.expiry,
        d.high,
        d.low
    FROM api_daily_stock_data d
    WHERE d.stock_code = in_stock_code
      AND d.date BETWEEN in_start_date AND in_end_date
    ORDER BY d.date ASC;
END;
$$;
