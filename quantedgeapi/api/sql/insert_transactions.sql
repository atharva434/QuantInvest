CREATE OR REPLACE FUNCTION place_option_order(
    p_stock_code TEXT,
    p_exchange_code TEXT,
    p_expiry_date DATE,
    p_right TEXT,
    p_strike_price NUMERIC,
    p_order_id TEXT,
    p_action TEXT,
    p_order_type TEXT,
    p_stop_loss INTEGER,
    p_quantity INTEGER
)
RETURNS VOID AS $$
DECLARE
    v_stock_id INTEGER;
    v_expiry_id INTEGER;
    v_option_id INTEGER;
BEGIN
    -- Step 1: Get Stock
    SELECT id INTO v_stock_id FROM api_stock
    WHERE stock_code = p_stock_code AND fno_exchange_code = p_exchange_code;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Stock not found';
    END IF;

    -- Step 2: Get Expiry Stock
    SELECT id INTO v_expiry_id FROM api_expiry_stock
    WHERE stock_id = v_stock_id AND expiry_date = p_expiry_date;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Expiry stock not found';
    END IF;

    -- Step 3: Get Option Chain
    SELECT oc.id INTO v_option_id FROM api_optionchain oc
    JOIN api_optionchainsummary ocs ON oc.option_chain_summary_id = ocs.id
    WHERE ocs.stock_expiry_id = v_expiry_id AND LOWER(oc.right) = LOWER(p_right)
      AND oc.strike_price = p_strike_price;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Option chain not found';
    END IF;

    -- Step 4: Insert Transaction
    INSERT INTO api_transactions (
        stock_id, stock_expiry_id, optionchain_id,
        order_id, action, order_type, stop_loss, quantity,
        validity, product_type
    ) VALUES (
        v_stock_id, v_expiry_id, v_option_id,
        p_order_id, LOWER(p_action), LOWER(p_order_type),
        p_stop_loss, p_quantity,
        'day', 'options'
    );
END;
$$ LANGUAGE plpgsql;