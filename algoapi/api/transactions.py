from django.db import connection
from datetime import datetime


def place_order_with_sp(stock_code, exchange_code, expiry_date, right, strike_price,
                        order_id, action, order_type, stop_loss, quantity):

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT place_option_order(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [
            stock_code, exchange_code, expiry_date, right, strike_price,
            order_id, action, order_type, stop_loss, quantity
        ])