CREATE OR REPLACE PROCEDURE delete_expiry(
    p_id INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM api_expiry WHERE id = p_id) THEN
        RAISE EXCEPTION 'No expiry record with id: %', p_id;
    END IF;

    DELETE FROM api_expiry WHERE id = p_id;
END;
$$;