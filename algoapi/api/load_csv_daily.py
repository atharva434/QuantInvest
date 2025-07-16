import pandas as pd
from django.db import connection
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "algoapi.settings")
django.setup()

def insert_from_excel(filepath):
    try:
        # Load both relevant sheets
        df_values = pd.read_excel(filepath, sheet_name='Historical_Data_Values')
        df_codes = pd.read_excel(filepath, sheet_name='Stock_Codes')
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    # Clean up empty/unwanted columns
    if df_values.columns[0].startswith('Unnamed') or df_values.iloc[:, 0].isnull().all():
        df_values = df_values.iloc[:, 1:]

    df_values.columns = df_values.columns.str.strip()
    df_codes.columns = df_codes.columns.str.strip()

    # Merge to map Stock_Code_Yahoo → Stock_Code (ICICI Direct)
    merged_df = pd.merge(
        df_values,
        df_codes[['Stock_Code_Yahoo', 'Stock_Code']],
        on='Stock_Code_Yahoo',
        how='left'
    )

    rows_inserted = 0
    rows_skipped = 0
    missing_mappings = []

    for _, row in merged_df.iterrows():
        try:
            stock_code = str(row['Stock_Code']).strip()

            # Skip if mapping not found
            if pd.isnull(stock_code) or stock_code == '':
                missing_mappings.append(row['Stock_Code_Yahoo'])
                raise ValueError("Missing ICICI Direct Stock_Code mapping")

            # Handle dates
            date = pd.to_datetime(row['Date'], unit='D', origin='julian').date() \
                if isinstance(row['Date'], (float, int)) else pd.to_datetime(row['Date']).date()

            open_val = float(row['Open'])
            high_val = float(row['High'])
            low_val = float(row['Low'])
            close_val = float(row['Close'])
            volume_val = int(float(row['Volume']))
            expiry = pd.to_datetime(row['Expiry Date']).date() if pd.notnull(row['Expiry Date']) else None

            # Debug print before insertion
            print(f"Trying to insert: {stock_code}, {date}, {open_val}, {high_val}, {low_val}, {close_val}, {volume_val}, {expiry}")

            # Call stored procedure to insert
            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL insert_daily_stock_data(%s, %s, %s, %s, %s, %s, %s, %s)",
                    [
                        stock_code,
                        date,
                        open_val,
                        high_val,
                        low_val,
                        close_val,
                        volume_val,
                        expiry
                    ]
                )
            rows_inserted += 1

        except Exception as e:
            rows_skipped += 1
            print(f"❌ Error inserting row {row.get('Stock_Code_Yahoo', '')} on {row.get('Date', '')}: {e}")

    # Final summary
    print(f"\n✅ Inserted: {rows_inserted} rows")
    print(f"❌ Skipped: {rows_skipped} rows")

    if missing_mappings:
        print("\n⚠ Missing Stock_Code mappings for these Stock_Code_Yahoo entries:")
        unique_missing = set(missing_mappings)
        for code in sorted(unique_missing):
            print(f" - {code}")


if __name__ == "__main__":
    insert_from_excel("api/Historical_Data_v2.xlsx")