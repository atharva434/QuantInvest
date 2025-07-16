CREATE OR REPLACE FUNCTION get_option_chain_data()
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_agg(data) INTO result
    FROM (
        SELECT 
            s."Stock_code" AS stock_code,
            s."SN" AS stock_name,
            s."Lot_size" AS lot_size,
            (
                SELECT json_agg(json_build_object('strikeprice', o.strikeprice, 'ltp', o.ltp))
                FROM "api_optionchain" o
                WHERE o.stock_code = s."Stock_code" AND o.ltp != 0
            ) AS entries,
            (
                SELECT json_agg(e.expiry_date)
                FROM "api_Expiry_Stock" e
                WHERE e.stock_code = s."Stock_code"
            ) AS expiry_dates
        FROM "api_stocklist" s
        WHERE s.status = TRUE
    ) AS data;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_unique_strikes(p_stock_code TEXT, p_right TEXT)
RETURNS TABLE(strike_price INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT oc.strike_price
    FROM api_optionchain oc
    JOIN api_optionchainsummary ocs ON oc.option_chain_summary_id = ocs.id
    JOIN api_expiry_stock es ON ocs.stock_expiry_id = es.id
    JOIN api_stock s ON es.stock_id = s.id
    WHERE s.stock_code = p_stock_code
      AND oc.right = LOWER(p_right);
END;
$$ LANGUAGE plpgsql;