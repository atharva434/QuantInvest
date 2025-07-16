-- DROP FUNCTION IF EXISTS view_expiries();
CREATE OR REPLACE FUNCTION view_expiries()
RETURNS TABLE(id BIGINT, month DATE, expiry_type VARCHAR, expiry_date DATE)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY 
    SELECT api_expiry.id, api_expiry.month, api_expiry.expiry_type, api_expiry.expiry_date 
    FROM api_expiry;
END;
$$;