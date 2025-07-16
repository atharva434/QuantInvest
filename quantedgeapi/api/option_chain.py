import logging
from django.db import connection
from collections import namedtuple
from decouple import config
from .yieldcalculator import *
from datetime import datetime
from api import stockexpiry
from .utils import get_atm_per
import json

logger = logging.getLogger(__name__)

def upsert_option_chain_summary(data):
    """
    This function performs an upsert operation for option chain summary in the database.

    :param data: A dictionary containing the option chain summary data to be upserted
    """
    try:
        # Log the data being upserted
        logger.debug(f"Attempting to upsert option chain summary with data: {data}")
        
        # Execute the stored procedure to upsert the option chain summary
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT upsert_option_chain_summary(%s, %s, %s, %s, %s, %s, %s)
            """, [
                data['stock_expiry_id'],
                data['cmp'],
                data['atm_strike'],
                data['atm_strike_pct'],
                data['start_of_strike'],
                data['margin_per_lot_sos'],
                data['datetime']
            ])
        
        # Log success
            logger.info("Option chain summary upserted successfully.")
            return cursor.fetchone()[0]
    
    except Exception as e:
        # Log the error
        logger.error(f"Error while upserting option chain summary: {e}")
        # Optionally, raise the error to propagate the issue
        raise

import logging
from django.db import connection

logger = logging.getLogger(__name__)

def bulk_insert_option_chain(summary_id, chain_list):
    try:
        if not chain_list:
            logger.warning("No chains to insert.")
            return

        right = []
        strike_price = []
        ltp = []
        best_bid_price = []
        best_bid_quantity = []
        best_offer_price = []
        best_offer_quantity = []
        open_ = []
        high = []
        low = []
        prev_close = []
        ltp_perc_change = []
        total_quantity_traded = []
        spot_price = []
        open_interest = []
        change_in_open_interest = []
        total_buy_quantity = []
        total_sell_quantity = []
        datetime_ = []

        for chain in chain_list:
            right.append(chain["right"])
            strike_price.append(chain["strike_price"])
            ltp.append(chain["ltp"])
            best_bid_price.append(chain["best_bid_price"])
            best_bid_quantity.append(chain["best_bid_quantity"])
            best_offer_price.append(chain["best_offer_price"])
            best_offer_quantity.append(chain["best_offer_quantity"])
            open_.append(chain["open"])
            high.append(chain["high"])
            low.append(chain["low"])
            prev_close.append(chain["previous_close"])
            ltp_perc_change.append(chain["ltp_percent_change"])
            total_quantity_traded.append(chain["total_quantity_traded"])
            spot_price.append(chain["spot_price"])
            open_interest.append(chain["open_interest"])
            change_in_open_interest.append(chain["chnge_oi"])
            total_buy_quantity.append(chain["total_buy_qty"])
            total_sell_quantity.append(chain["total_sell_qty"])
            datetime_.append(datetime.now())

        with connection.cursor() as cursor:
            cursor.execute("""
                    SELECT bulk_insert_option_chain(
        %s::BIGINT,
        %s::TEXT[],
        %s::INT[],
        %s::DOUBLE PRECISION[],
        %s::DOUBLE PRECISION[],
        %s::INT[],
        %s::DOUBLE PRECISION[],
        %s::INT[],
        %s::DOUBLE PRECISION[],
        %s::DOUBLE PRECISION[],
        %s::DOUBLE PRECISION[],
        %s::DOUBLE PRECISION[],
        %s::DOUBLE PRECISION[],
        %s::INT[],
        %s::DOUBLE PRECISION[],
        %s::INT[],
        %s::DOUBLE PRECISION[],
        %s::INT[],
        %s::INT[],
        %s::TIMESTAMP[]
    );
            """, [
                summary_id, right, strike_price, ltp, best_bid_price, best_bid_quantity,
                best_offer_price, best_offer_quantity, open_, high, low, prev_close,
                ltp_perc_change, total_quantity_traded, spot_price, open_interest,
                change_in_open_interest, total_buy_quantity, total_sell_quantity, datetime_
            ])

        logger.info(f"Bulk insert completed for {len(chain_list)} option chains.")

    except Exception as e:
        logger.exception("Error while inserting option chains in bulk.")

def save_optionchain(breeze, stock_info, expiry_date, base_ltp, right, exchange_code):
    import logging
    from datetime import datetime

    logger = logging.getLogger(__name__)
    try:
        stock_code = stock_info["stock_code"]
        atm_per = get_atm_per(stock_code=stock_code, stock_type=stock_info["stock_type"], right=right)
        threshold_strike = base_ltp * (1 + atm_per / 100)
        try: 
            expiry_date = datetime.strptime(expiry_date, "%B %d, %Y").strftime("%Y-%m-%d")
        except:
            expiry_date = expiry_date
        option_chains = get_option_chain(breeze, stock_code,right=right ,expiry_date=expiry_date, exchange_code=exchange_code)

        data = {}
        summary_id = None
        bulk_chains = []
        capture = False

        for chain in option_chains:
            strike = chain["strike_price"]
            bulk_chains.append({
                **chain,
                "right": chain["right"].lower(),
                "datetime": datetime.now()
            })

            if summary_id is None and strike >= threshold_strike:
                # Get margin for this strike
                margin = get_margin(
                    breeze, stock_code, strike,
                    chain["ltp"], stock_info["lot_size"],
                    expiry_date, right=right
                )

                expiry_id = stockexpiry.get_stock_expiry_id(stock_code, expiry_date)

                data = {
                    'stock_expiry_id': expiry_id,
                    'cmp': base_ltp,
                    'atm_strike': strike,
                    'atm_strike_pct': atm_per,
                    'start_of_strike': threshold_strike,
                    'margin_per_lot_sos': margin,
                    'datetime': datetime.now()
                }

                summary_id = upsert_option_chain_summary(data)
        if summary_id and bulk_chains:
            bulk_insert_option_chain(summary_id, bulk_chains)

        logger.info(f"Option chain summary and data saved for {stock_code}, expiry {expiry_date}")

    except Exception as e:
        logger.error(f"Error in save_optionchain_summary for {stock_info['stock_code']}: {str(e)}", exc_info=True) 

def fetch_option_data():
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_full_data()")
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    


def get_strikes_by_stock_and_right(stock_code, right):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_unique_strikes(%s, %s)", [stock_code, right])
        rows = cursor.fetchall()
        return [row[0] for row in rows] 
    


