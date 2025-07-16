CREATE OR REPLACE FUNCTION upsert_option_chain_summary(
    p_expiry_stock_id BIGINT,
    p_cmp NUMERIC,
    p_atm_strike NUMERIC,
    p_atm_strike_pct INTEGER,
    p_start_of_strike NUMERIC,
    p_margin_per_lot_sos NUMERIC,
    p_datetime TIMESTAMP
)
RETURNS BIGINT AS $$
DECLARE
    result_id BIGINT;
BEGIN
    INSERT INTO api_optionchainsummary (
        stock_expiry_id,
        cmp,
        atm_strike,
        atm_strike_pct,
        start_of_strike,
        margin_per_lot_sos,
        datetime
    )
    VALUES (
        p_expiry_stock_id,
        p_cmp,
        p_atm_strike,
        p_atm_strike_pct,
        p_start_of_strike,
        p_margin_per_lot_sos,
        p_datetime
    )
    ON CONFLICT (stock_expiry_id, datetime)
    DO UPDATE SET
        cmp = EXCLUDED.cmp,
        atm_strike = EXCLUDED.atm_strike,
        atm_strike_pct = EXCLUDED.atm_strike_pct,
        start_of_strike = EXCLUDED.start_of_strike,
        margin_per_lot_sos = EXCLUDED.margin_per_lot_sos
    RETURNING id INTO result_id;

    RETURN result_id;
END;
$$ LANGUAGE plpgsql;