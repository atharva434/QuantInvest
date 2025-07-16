CREATE OR REPLACE FUNCTION delete_stock(p_id INTEGER)
RETURNS VOID AS $$
BEGIN

    -- Then delete the parent stock
    DELETE FROM api_stock WHERE id = p_id;
END;
$$ LANGUAGE plpgsql;