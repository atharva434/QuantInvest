DROP FUNCTION IF EXISTS get_full_data();
CREATE OR REPLACE FUNCTION get_full_data()
RETURNS TABLE (
    stock_code VARCHAR,
    stock_name VARCHAR,
    lot_size INTEGER,
    expiry_date DATE,
    strike_price INTEGER,
    cmp FLOAT,
    ltp FLOAT,
    margin FLOAT,
    right VARCHAR,
    start_of_strike INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.stock_code,
        s.stock_name,
        s.lot_size,
        es.expiry_date,
        oc.strike_price,
        ocs.cmp,
        oc.ltp,
        ocs.margin_per_lot_sos AS margin,
        oc.right,
        ocs.start_of_strike
    FROM (
        SELECT DISTINCT ON (s.id, es.expiry_date)
            ocs.*
        FROM api_optionchainsummary ocs
        JOIN api_expiry_stock es ON es.id = ocs.stock_expiry_id
        JOIN api_stock s ON s.id = es.stock_id
        ORDER BY s.id, es.expiry_date, ocs.datetime DESC
    ) AS ocs
    JOIN api_expiry_stock es ON es.id = ocs.stock_expiry_id
    JOIN api_stock s ON s.id = es.stock_id
    JOIN api_optionchain oc ON oc.option_chain_summary_id = ocs.id;
END;
$$ LANGUAGE plpgsql;