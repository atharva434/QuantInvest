CREATE OR REPLACE PROCEDURE delete_expiry_stock(p_id INTEGER)
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM api_expiry_stock WHERE id = p_id;
END;
$$;