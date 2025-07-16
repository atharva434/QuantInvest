from django.http import JsonResponse
import pandas as pd
from datetime import date, timedelta
from django.db import connection
from api import yieldcalculator
from decouple import config
import logging
from collections import namedtuple


logger = logging.getLogger(__name__)

def get_stock_info_by_id(stock_code):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_stock_info_by_code(%s);", [stock_code])
        row = cursor.fetchone()
    
    if row:
        return {
            'id': row[0],
            'stock_code': row[1],
            'stock_name': row[2],
            'lot_size': row[3],
            'exchange_code': row[4],
            'stock_type': row[5],
            'fno_exchange_code': row[6],
        }
    return None

def fetch_valid_stock_codes():
    """Call stored function to get stock codes available in both tables."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_valid_stock_codes()")
        return [row[0] for row in cursor.fetchall()]
    
def fetch_daily_stock_data(stock_code, start_date, end_date):
    """
    Fetches historical daily stock data for a given stock_code and date range.
    """
    logger.info(f"Fetching daily data for {stock_code} from {start_date} to {end_date}")

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM fetch_historical_stock_data_range(%s, %s, %s)
            """, [stock_code, start_date, end_date])

            desc = cursor.description
            StockData = namedtuple("DailyStockData", [col[0] for col in desc])
            data = [StockData(*row) for row in cursor.fetchall()]

        logger.info(f"Fetched {len(data)} rows for {stock_code}")
        return data

    except Exception as e:
        logger.error(f"Failed to fetch daily stock data: {e}", exc_info=True)
        return []
  
def get_expiry_close_from_rows(df: pd.DataFrame, current_expiry_date: date):
    """
    Returns the closing price on or just before the previous expiry date
    prior to the given current_expiry_date from the given DataFrame.
    """
    expiry_rows = df[df["Expiry Date"] < current_expiry_date]
    if expiry_rows.empty:
        return None

    prev_expiry = expiry_rows["Expiry Date"].max()
    exact_match = df[df["Date"] == prev_expiry]
    if not exact_match.empty:
        return exact_match.iloc[0]["Close"]

    fallback = df[df["Date"] < prev_expiry]
    if fallback.empty:
        return None

    return fallback.sort_values("Date", ascending=False).iloc[0]["Close"]



def get_nearest_valid_strike(stock_code: str, strike_target: float):
    """
    Fetches the nearest valid strike price for a stock based on strike_target.
    Strike prices are pulled from the get_full_data() database function.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_full_data()")
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    # Filter only relevant strikes
    filtered_strikes = {
        float(row["strike_price"])
        for row in rows
        if row.get("stock_code") == stock_code
    }

    if not filtered_strikes:
        return None

    return min(filtered_strikes, key=lambda s: abs(s - strike_target))

def process_days_moves(moves, cmp, stock_code, name_prefix="days_to_expiry"):
    """
    Processes pseudo expiry moves and maps them into movement buckets.
    Returns a dict with counts and nearest strike prices for each bucket.
    """
    buckets = {
        'pos_0_5': 5,
        'pos_5_10': 10,
        'pos_10_15': 15,
        'pos_15_20': 20,
        'pos_20_25': 25,
        'pos_25': 30,
        'neg_0_5': -5,
        'neg_5_10': -10,
        'neg_10_15': -15,
        'neg_15_20': -20,
        'neg_20_25': -25,
        'neg_25': -30,
    }

    result = {}

    # Initialize counts
    bucket_counts = {bucket: 0 for bucket in buckets}

    # Count entries in each bucket
    for move in moves:
        try:
            pct = float(move.get('percent_move', 0))
        except (ValueError, TypeError):
            continue

        for bucket, fixed_pct in buckets.items():
            low = fixed_pct - 5 if fixed_pct > 0 else fixed_pct
            high = fixed_pct if fixed_pct > 0 else fixed_pct + 5
            if low <= pct < high:
                bucket_counts[bucket] += 1
                break

    # Populate final result with count + nearest strike
    for bucket, fixed_pct in buckets.items():
        result[f"{bucket}_{name_prefix}"] = bucket_counts[bucket]

        strike_target = round(cmp * (1 + fixed_pct / 100))
        result[f"{bucket}_{name_prefix}_strike"] = strike_target

    return result

def process_monthly_moves(moves, stock_code, df, name_prefix="monthly"):
    """
    Processes monthly expiry moves and maps them into movement buckets.
    Uses last month's expiry close as the base to compute nearest valid strikes.
    """

    # Define movement buckets
    buckets = {
        'pos_0_5': 5,
        'pos_5_10': 10,
        'pos_10_15': 15,
        'pos_15_20': 20,
        'pos_20_25': 25,
        'pos_25': 30,
        'neg_0_5': -5,
        'neg_5_10': -10,
        'neg_10_15': -15,
        'neg_15_20': -20,
        'neg_20_25': -25,
        'neg_25': -30,
    }

    result = {}

    # Step 1: Count entries in each bucket
    bucket_counts = {bucket: 0 for bucket in buckets}
    for move in moves:
        try:
            pct = float(move.get('percent_move') or move.get('pct_move', 0))
        except (ValueError, TypeError):
            continue

        for bucket, fixed_pct in buckets.items():
            low = fixed_pct - 5 if fixed_pct > 0 else fixed_pct
            high = fixed_pct if fixed_pct > 0 else fixed_pct + 5
            if low <= pct < high:
                bucket_counts[bucket] += 1
                break

    # Step 2: Find last expiry before today
    today = date.today()
    past_expiries = df[df["Expiry Date"].notna() & (df["Expiry Date"] <= today)]
    if past_expiries.empty:
        print("[⚠️ Warning] No expiry data before today found!")
        return result

    latest_expiry = past_expiries["Expiry Date"].max()
    print(f"[📅 Last Expiry Found] {latest_expiry}")

    # Step 3: Try to get the close price on expiry
    expiry_close_row = df[df["Date"] == latest_expiry]
    if not expiry_close_row.empty:
        base_close = float(expiry_close_row.iloc[0]["Close"])
        print(f"[✅ Using Expiry Close] {base_close} on {latest_expiry}")
    else:
        # Fallback: find latest available close before expiry
        fallback_rows = df[df["Date"] < latest_expiry].sort_values("Date", ascending=False)
        if fallback_rows.empty:
            print("[🚫 No fallback close found]")
            return result
        base_close = float(fallback_rows.iloc[0]["Close"])
        print(f"[🔁 Using Fallback Close] {base_close} on {fallback_rows.iloc[0]['Date']}")

    # Step 4: Compute strikes and populate result
    for bucket, fixed_pct in buckets.items():
        result[f"{bucket}_{name_prefix}"] = bucket_counts[bucket]

        strike_target = round(base_close * (1 + fixed_pct / 100))

        print(f"[🎯 {bucket}] Base: {base_close}, Target: {strike_target}")

        result[f"{bucket}_{name_prefix}_strike"] = strike_target

    return result




def get_cmp_and_strikes_for_stock(stock_code, breeze):
    """
    Returns CMP, ATM strike, and nearest valid strike price for a given stock_code.
    """
    from datetime import datetime

    try:
        cmp = yieldcalculator.get_ltp(breeze=breeze, stock_code=stock_code)["ltp"]
    except Exception as e:
        print(f"[❌] Error fetching LTP for {stock_code}: {e}")
        return None, None, None

    if not cmp:
        print(f"[⚠️] No CMP found for {stock_code}")
        return None, None, None

    stock_info = get_stock_info_by_id(stock_code)
    stock_type = stock_info.get("stock_type", "equity") if stock_info else "equity"
    atm_per_key = "ATM_PER_EQ" if stock_type == "equity" else "ATM_PER_IND"
    atm_per = config(atm_per_key, cast=int, default=5)
    atm_strike = round(cmp * (1 + atm_per / 100), 2)
    print(f"[INFO] {stock_code} - CMP: {cmp}, ATM Strike: {atm_strike}")

    today = date.today()
    valid_strikes = set()

    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_full_data()")
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    print(f"\n[🔍 DEBUG] Rows fetched from get_full_data(): {len(rows)}\n")

    for row in rows:
        sc = row.get('stock_code', '').strip().upper()
        right = row.get('right', '').upper()
        ltp = row.get('ltp')
        expiry = row.get('expiry_date')
        strike = row.get('strike_price')

        if sc != stock_code.strip().upper():
            continue

        print(f"[ROW] {sc} | Right: {right} | LTP: {ltp} | Expiry: {expiry} | Strike: {strike}")

        # Skip if not CALL or PUT
        if right not in ['CALL', 'PUT']:
            print(f"    ⛔ Skipped: Invalid right = {right}")
            continue

        # Skip if LTP is zero or None
        # if not ltp or float(ltp) == 0:
        #     print(f"    ⛔ Skipped: LTP is 0 or None")
        #     continue

        # Parse expiry to date if needed
        if isinstance(expiry, str):
            expiry = datetime.strptime(expiry, "%Y-%m-%d").date()

        if not expiry or expiry < today:
            print(f"    ⛔ Skipped: Expiry is missing or in the past")
            continue

        if strike is None:
            print(f"    ⛔ Skipped: Strike is None")
            continue

        valid_strikes.add(float(strike))
        print(f"    ✅ Accepted Strike: {strike}")

    print(f"\n[✅] Valid Strikes for {stock_code}: {sorted(valid_strikes)}")
    nearest_strike = min(valid_strikes, key=lambda s: abs(s - atm_strike)) if valid_strikes else None
    print(f"[🎯] Nearest Strike for {stock_code}: {nearest_strike}\n")

    return round(cmp, 2), round(atm_strike, 2), nearest_strike


def get_pseudo_vs_expiry_moves(df, start_date, end_date, days_to_expiry):
    """
    For each expiry, compare the close price on pseudo_date (expiry - days_to_expiry)
    with the expiry date close price.

    Returns: dict {expiry_date_str: {pseudo_date, expiry_date, pseudo_close, expiry_close, percent_move}}
    """
    df['Date'] = pd.to_datetime(df['Date'])
    df['Expiry Date'] = pd.to_datetime(df['Expiry Date'], errors='coerce')

    if isinstance(start_date, str) or isinstance(start_date, pd.Timestamp):
        start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str) or isinstance(end_date, pd.Timestamp):
        end_date = pd.to_datetime(end_date)

    all_moves = {}
    unique_expiries = sorted(df['Expiry Date'].dropna().unique())

    for expiry_date in unique_expiries:
        pseudo_date = expiry_date - timedelta(days=days_to_expiry)

        if expiry_date < start_date or pseudo_date > end_date:
            continue

        expiry_row = df[(df['Date'] == expiry_date) & (df['Expiry Date'] == expiry_date)]
        pseudo_row = df[df['Date'] == pseudo_date]

        if expiry_row.empty or pseudo_row.empty:
            continue

        expiry_close = expiry_row.iloc[0]['Close']
        pseudo_close = pseudo_row.iloc[0]['Close']

        if pd.isna(expiry_close) or pd.isna(pseudo_close) or pseudo_close == 0:
            continue

        percent_move = round(((expiry_close - pseudo_close) / pseudo_close) * 100, 2)

        all_moves[expiry_date.strftime('%Y-%m-%d')] = {
            'pseudo_date': pseudo_date.strftime('%Y-%m-%d'),
            'expiry_date': expiry_date.strftime('%Y-%m-%d'),
            'pseudo_close': float(pseudo_close),
            'expiry_close': float(expiry_close),
            'percent_move': percent_move
        }

    return all_moves

def calculate_monthly_moves_from_expiry(df, start_date, end_date):
    """
    Calculate monthly % moves using expiry-to-expiry date logic.
    
    Returns:
        List of dicts with:
        - 'month'
        - 'start_date'
        - 'end_date'
        - 'pct_move'
    """
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df['Expiry Date'] = pd.to_datetime(df['Expiry Date'], errors='coerce').dt.date

    if isinstance(start_date, str) or isinstance(start_date, pd.Timestamp):
        start_date = pd.to_datetime(start_date).date()
    if isinstance(end_date, str) or isinstance(end_date, pd.Timestamp):
        end_date = pd.to_datetime(end_date).date()

    df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)].copy()

    expiry_dates = sorted(
        d for d in df['Expiry Date'].dropna().unique()
        if start_date <= d <= end_date
    )

    if len(expiry_dates) < 2:
        return []

    monthly_moves = []

    for i in range(1, len(expiry_dates)):
        prev_expiry = expiry_dates[i - 1]
        current_expiry = expiry_dates[i]

        first_row = df[df['Date'] >= prev_expiry].sort_values('Date').head(1)
        last_row = df[df['Date'] <= current_expiry].sort_values('Date', ascending=False).head(1)

        if first_row.empty or last_row.empty:
            continue

        first_close = first_row.iloc[0]['Close']
        last_close = last_row.iloc[0]['Close']

        if pd.isna(first_close) or pd.isna(last_close) or first_close == 0:
            continue

        pct_move = round(((last_close - first_close) / first_close) * 100, 2)

        monthly_moves.append({
            'month': current_expiry.strftime('%B %Y'),
            'start_date': prev_expiry,
            'end_date': current_expiry,
            'pct_move': pct_move
        })

    return monthly_moves

def get_expiry_dates_for_stock(stock_code):
    """
    Returns a list of expiry dates for the given stock_code.
    Each date is returned as a dict with 'raw' and 'display' keys.
    """
    expiry_dates = []

    if not stock_code:
        return []

    from . import stock  # Ensure stock module is imported

    stocks = stock.fetch_all_stocks()
    stock_obj = next((s for s in stocks if s.stock_code == stock_code), None)

    if stock_obj:
        expiry_dates = stock.fetch_future_expiry_dates(stock_obj.id)

    return [{'raw': d.isoformat(), 'display': d.strftime('%d-%m-%Y')} for d in expiry_dates]

def get_valid_expiries():
    """
    Returns a list of expiry dates for the given stock_code.
    Each date is returned as a dict with 'raw' and 'display' keys.
    """
    from . import stock
    expiry_dates = []


    stocks = stock.fetch_all_stocks()
    for stk in stocks:
        try:
            expiry_dates = stock.fetch_future_expiry_dates(stk.id)
            break
        except:
            continue
    weekly_stocks = ["NIFTY"]
    expiry_dates = set(expiry_dates)
    for weekly_stock in weekly_stocks:
        stock_id = stock.get_stock_info_by_code(weekly_stock)["id"]
        print(stock.fetch_future_expiry_dates(stock_id=stock_id))
        expiry_dates.update(stock.fetch_future_expiry_dates(stock_id=stock_id))

    return list(expiry_dates)


def get_analysis_inputs(stock_code, expiry_date, breeze):
    """
    Fetches CMP, ATM Strike, nearest strike, days to expiry, and min/max dates for a stock.
    Returns a dictionary with all required fields.
    """
    if not stock_code or not expiry_date:
        return {'error': 'Missing stock_code or expiry_date'}

    # Get CMP, ATM Strike, Nearest Strike
    cmp, atm_strike, nearest_strike = get_cmp_and_strikes_for_stock(stock_code, breeze)
    print(nearest_strike)
    if not cmp:
        return {'error': 'Failed to get CMP/ATM'}

    # Get min/max date from DB
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM get_min_max_for_stock_code(%s)", [stock_code])
            result = cursor.fetchone()
            _, _, min_date, max_date = result if result else (None, None, None, None)
    except Exception as e:
        print(f"Error fetching min/max date: {e}")
        return {'error': 'Failed to get min/max date'}

    # Calculate days to expiry
    try:
        today = date.today()
        expiry = date.fromisoformat(expiry_date)
        days_to_expiry = (expiry - today).days
    except Exception as e:
        print(f"Invalid expiry date: {e}")
        return {'error': 'Invalid expiry_date format'}

    return {
        'stock_code': stock_code,
        'cmp': cmp,
        'atm_strike': nearest_strike,  # Using nearest strike
        'today': today.isoformat(),
        'expiry_date': expiry.isoformat(),
        'days_to_expiry': days_to_expiry,
        'min_date': min_date.strftime('%Y-%m-%d') if min_date else None,
        'max_date': max_date.strftime('%Y-%m-%d') if max_date else None,
        'start_date': today.strftime('%Y-%m-%d'),
    }

def get_stock_min_max_info(stock_code):
    """
    Fetches stock_id, stock_code, min_date, and max_date from DB for a given stock_code.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_min_max_for_stock_code(%s)", [stock_code])
        row = cursor.fetchone()
    if not row:
        return None

    stock_id, code, min_date, max_date = row
    return {
        'stock_id': stock_id,
        'stock_code': code,
        'min_date': min_date.isoformat() if min_date else None,
        'max_date': max_date.isoformat() if max_date else None
    }

def get_stock_id(stock_code):
    """Fetch stock_id from the api_stock table using stock_code."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM api_stock WHERE stock_code = %s", [stock_code])
        result = cursor.fetchone()
        return result[0] if result else None