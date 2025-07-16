CREATE OR REPLACE PROCEDURE update_expiry(
    p_id INTEGER,
    p_month DATE,
    p_expiry_type VARCHAR,
    p_expiry_date DATE
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM api_expiry WHERE id = p_id) THEN
        RAISE EXCEPTION 'No expiry record with id: %', p_id;
    END IF;

    IF p_expiry_type NOT IN ('weekly', 'monthly') THEN
        RAISE EXCEPTION 'Invalid expiry type: %', p_expiry_type;
    END IF;

    UPDATE api_expiry
    SET month = p_month,
        expiry_type = p_expiry_type,
        expiry_date = p_expiry_date
    WHERE id = p_id;
END;
$$;