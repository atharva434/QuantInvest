from .utils import get_date_range
from datetime import date
import logging

logger = logging.getLogger(__name__)

def get_trade_list(breeze, num_days=10):
    from_date_str, to_date_str = get_date_range(num_days)
    positions = breeze.get_trade_list(from_date=from_date_str,
                        to_date=to_date_str,
                        exchange_code="NFO",
                        product_type="",
                        action="",
                        stock_code="")
    logger.info(f"Fetching trade list from {from_date_str} to {to_date_str}")
    try:
        return positions["Success"]
    
    except:
        logger.error("Failed to fetch trade list", exc_info=True)
        return []
    

def get_open_positions(breeze):
    positions = breeze.get_portfolio_positions()
    logger.info("Fetching open portfolio positions")
    try:
        return positions["Success"]
    except:
        logger.error("Failed to fetch open positions", exc_info=True)
        return []


def get_portfolio_holdings(breeze):
    today = date.today()
    start_of_month = today.replace(day=1)

    from_date_str = start_of_month.strftime('%Y-%m-%d')
    to_date_str = today.strftime('%Y-%m-%d')

    positions = breeze.get_portfolio_holdings(
        exchange_code="NFO",
        from_date=from_date_str,
        to_date=to_date_str,
    )
    logger.info(f"Fetching portfolio holdings from {from_date_str} to {to_date_str}")
    try:
        return positions["Success"]
    except:
        logger.error("Failed to fetch portfolio holdings", exc_info=True)
        return []