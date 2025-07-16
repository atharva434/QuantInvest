from django.db import connection
import logging
from collections import namedtuple
from datetime import datetime as dt
from .yieldcalculator import *
logger = logging.getLogger(__name__)

def save_stock_price(breeze, stock_code, stock_id, stock_name, exchange_code):
    json_data = get_ltp(breeze, stock_code, exchange_code)
    try:
        date_str = dt.now().strftime('%Y-%m-%d')  # or derive from `json_data` if needed
        timestamp = dt.now()

        open_val = json_data.get('open', 0.0)
        high_val = json_data.get('high', 0.0)
        low_val = json_data.get('low', 0.0)
        close_val = json_data.get('ltp', 0.0)
        volume = float(json_data.get('total_quantity_traded', '0') or 0.0)

        with connection.cursor() as cursor:
            cursor.callproc('upsert_stock_price', [
                stock_id,
                date_str,
                open_val,
                high_val,
                low_val,
                close_val,
                volume,
                timestamp
            ])
        logger.info(f"Upserted stock price for {stock_name} on {date_str}")
        return close_val
    except Exception as e:
        logger.error(f"Error inserting stock price for {stock_name}: {str(e)}")