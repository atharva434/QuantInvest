from datetime import date
from django.db import connection


def get_grouped_option_chain():
    today = date.today()
    ltp_missing_codes = set()
    option_data_grouped = {}

    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_full_data()")
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    stock_groups = {}
    for row in rows:
        base_code = row['stock_code']
        right = row.get('right', '').upper()
        if right not in ['CALL', 'PUT']:
            continue
        stock_code = f"{base_code}_{right}"
        stock_groups.setdefault(stock_code, []).append(row)

    for stock_code, stock_rows in stock_groups.items():
        valid_rows = [r for r in stock_rows if r['ltp'] != 0 and r['expiry_date'] >= today]

        if not valid_rows:
            ltp_missing_codes.add(stock_code)
            continue

        first_row = valid_rows[0]
        start_strike = first_row['start_of_strike']

        option_data_grouped[stock_code] = {
            'stock_name': first_row['stock_name'],
            'lot_size': first_row['lot_size'],
            'cmp': first_row['cmp'],
            'stock_rows': [],
            'unique_expiry_dates': set()
        }

        seen = set()
        for row in valid_rows:
            key = (row['strike_price'], row['expiry_date'])
            if key not in seen:
                seen.add(key)

                ltp = row.get('ltp') or 0
                lot_size = row.get('lot_size') or 0
                margin = row.get('margin') or 0
                yield_value = (ltp * lot_size / margin * 100) if margin else 0
                row['yield'] = round(yield_value, 2)

                option_data_grouped[stock_code]['stock_rows'].append(row)
                option_data_grouped[stock_code]['unique_expiry_dates'].add(row['expiry_date'])

        sorted_strikes = sorted(r['strike_price'] for r in option_data_grouped[stock_code]['stock_rows'])
        selected_strike = next((sp for sp in sorted_strikes if sp > start_strike), None)
        option_data_grouped[stock_code]['start_of_strike'] = selected_strike
        option_data_grouped[stock_code]['unique_expiry_dates'] = sorted(option_data_grouped[stock_code]['unique_expiry_dates'])

    return option_data_grouped, ltp_missing_codes