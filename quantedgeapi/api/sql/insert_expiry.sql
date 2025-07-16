CREATE OR REPLACE PROCEDURE insert_expiry(
    p_month DATE,
    p_expiry_type VARCHAR,
    p_expiry_date DATE
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_expiry_type NOT IN ('weekly', 'monthly') THEN
        RAISE EXCEPTION 'Invalid expiry type: %', p_expiry_type;
    END IF;

    INSERT INTO api_expiry (month, expiry_type, expiry_date)
    VALUES (p_month, p_expiry_type, p_expiry_date);
END;
$$;