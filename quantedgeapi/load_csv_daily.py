import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "quantedgeapi.settings")
django.setup()

import pandas as pd
from django.db import connection
from api.analysis import get_stock_id

def insert_from_excel(filepath):
    print("🚀 Starting to load daily stock data...")
    try:
        df_values = pd.read_excel(filepath, sheet_name="Historical_Data_Values")
        df_codes = pd.read_excel(filepath, sheet_name="Stock_Codes")
    except Exception as e:
        print(f"❌ Error reading Excel: {e}")
        return

    df_values.columns = df_values.columns.str.strip()
    df_codes.columns = df_codes.columns.str.strip()

    # 🔥 Pre-check: Exit early if no new *valid* data
    try:
        df_valid = df_values[
            (df_values['Open'] > 0) &
            (df_values['High'] > 0) &
            (df_values['Low'] > 0) &
            (df_values['Close'] > 0) &
            (df_values['Volume'] > 0)
        ]
        if df_valid.empty:
            print("❌ No valid OHLCV rows found in Excel. Exiting.")
            return

        max_excel_date = pd.to_datetime(df_valid['Date'], errors='coerce').max().date()
        print(f"📅 Excel max valid date: {max_excel_date}")

        with connection.cursor() as cursor:
            cursor.execute("SELECT MAX(date) FROM api_daily_stock_data")
            result = cursor.fetchone()
            max_db_date = result[0]
        print(f"📅 Max DB date: {max_db_date}")

        if max_db_date and max_excel_date <= max_db_date:
            print(f"✅ No new data to insert. DB already has up to {max_db_date}, Excel has up to {max_excel_date}")
            return
        else:
            print(f"📈 New data found. Excel max date: {max_excel_date}, DB max date: {max_db_date}")
    except Exception as e:
        print(f"⚠️ Skipping pre-check due to error: {e}")

    # Merge stock code mapping
    merged = pd.merge(
        df_values,
        df_codes[['Stock_Code_Yahoo', 'Stock_Code']],
        on='Stock_Code_Yahoo',
        how='left'
    )

    inserted = 0
    skipped = 0
    for _, row in merged.iterrows():
        try:
            stock_code = str(row['Stock_Code']).strip()
            if pd.isnull(stock_code) or stock_code == "":
                raise ValueError("Missing ICICI stock_code")

            stock_id = get_stock_id(stock_code)
            if not stock_id:
                raise ValueError(f"Stock ID not found for {stock_code}")

            date = pd.to_datetime(row['Date'], errors='coerce').date()
            open_ = float(row['Open'])
            high = float(row['High'])
            low = float(row['Low'])
            close = float(row['Close'])
            volume = int(float(row['Volume']))
            expiry = pd.to_datetime(row['Expiry Date'], errors='coerce').date() if pd.notnull(row['Expiry Date']) else None

            with connection.cursor() as cursor:
                cursor.execute("""
                               CALL insert_daily_stock_data(%s::text, %s, %s, %s, %s, %s, %s, %s, %s)""", 
                               [stock_code, stock_id, date, open_, high, low, close, volume, expiry])

            inserted += 1
        except Exception as e:
            skipped += 1
            print(f"⚠️ Skipped: {row.get('Stock_Code_Yahoo', 'N/A')} on {row.get('Date', 'N/A')} due to {e}")

    print(f"\n✅ Inserted: {inserted}")
    print(f"❌ Skipped: {skipped}")
    print("✅ Done loading daily stock data.")

if __name__ == "__main__":
    insert_from_excel("Historical_Data_v2.xlsx")

