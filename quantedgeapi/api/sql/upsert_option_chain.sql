-- ============================================
-- File: bulk_insert_option_chain.sql
-- Description: Bulk insert procedure for OptionChain table
-- ============================================

CREATE OR REPLACE FUNCTION bulk_insert_option_chain(
    p_option_chain_summary_id BIGINT,
    p_right TEXT[],
    p_strike_price INT[],
    p_ltp DOUBLE PRECISION[],
    p_best_bid_price DOUBLE PRECISION[],
    p_best_bid_quantity INT[],
    p_best_offer_price DOUBLE PRECISION[],
    p_best_offer_quantity INT[],
    p_open DOUBLE PRECISION[],
    p_high DOUBLE PRECISION[],
    p_low DOUBLE PRECISION[],
    p_prev_close DOUBLE PRECISION[],
    p_ltp_perc_change DOUBLE PRECISION[],
    p_total_quantity_traded INT[],
    p_spot_price DOUBLE PRECISION[],
    p_open_interest INT[],
    p_change_in_open_interest DOUBLE PRECISION[],
    p_total_buy_quantity INT[],
    p_total_sell_quantity INT[],
    p_datetime TIMESTAMP[]
)
RETURNS VOID AS $$
DECLARE
    idx INT := 1;
BEGIN
    WHILE idx <= array_length(p_strike_price, 1) LOOP
        INSERT INTO api_optionchain (
            option_chain_summary_id,
            "right",
            strike_price,
            ltp,
            best_bid_price,
            best_bid_quantity,
            best_offer_price,
            best_offer_quantity,
            open,
            high,
            low,
            prev_close,
            ltp_perc_change,
            total_quantity_traded,
            spot_price,
            open_interest,
            change_in_open_interest,
            total_buy_quantity,
            total_sell_quantity,
            datetime
        ) VALUES (
            p_option_chain_summary_id,
            p_right[idx],
            p_strike_price[idx],
            p_ltp[idx],
            p_best_bid_price[idx],
            p_best_bid_quantity[idx],
            p_best_offer_price[idx],
            p_best_offer_quantity[idx],
            p_open[idx],
            p_high[idx],
            p_low[idx],
            p_prev_close[idx],
            p_ltp_perc_change[idx],
            p_total_quantity_traded[idx],
            p_spot_price[idx],
            p_open_interest[idx],
            p_change_in_open_interest[idx],
            p_total_buy_quantity[idx],
            p_total_sell_quantity[idx],
            p_datetime[idx]
        );
        idx := idx + 1;
    END LOOP;
END;
$$ LANGUAGE plpgsql;