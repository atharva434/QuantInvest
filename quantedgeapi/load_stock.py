import pandas as pd
from django.db import connection
import os
import django

import csv
from pathlib import Path
from datetime import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "quantedgeapi.settings")
django.setup()
from api.models import Stock, Expiry_Stock


def load_stocks_from_csv(csv_path: str):
    csv_file = Path(csv_path)
    
    if not csv_file.exists():
        print(f"❌ File not found: {csv_path}")
        return

    with open(csv_file, newline='') as file:
        reader = csv.DictReader(file)

        for row in reader:
            try:
                stock_code = row['stock_code'].strip()
                
                # Check if the stock already exists
                if Stock.objects.filter(stock_code=stock_code).exists():
                    print(f"⚠️ Stock already exists: {stock_code}")
                    return

                stock = Stock(
                    stock_code=stock_code,
                    stock_name=row['stock_name'].strip(),
                    lot_size=int(row['lot_size']),
                    exchange_code=row['exchange_code'].strip(),
                    stock_type=row['stock_type'].strip(),
                    fno_exchange_code=row['fno_exchange_code'].strip(),
                )
                stock.save()
                print(f"✅ Saved stock: {stock.stock_code}")

            except Exception as e:
                print(f"❌ Error on row: {e}")
                continue


def populate_expiry_stock(csv_path: str):
    try:
        with open(csv_path) as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    stock_code = row['stock_code']
                    expiry_month = row['month']  # e.g., "APR-2025"
                    expiry_date_str = row['expiry_date']  # e.g., "2025-04-24"

                    # Parse expiry_date string to date object
                    expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()

                    # Get stock
                    stock = Stock.objects.get(stock_code=stock_code)

                    # Avoid duplicates
                    if not Expiry_Stock.objects.filter(stock=stock, expiry_date=expiry_date).exists():
                        Expiry_Stock.objects.create(
                            stock=stock,
                            month=expiry_month,
                            expiry_date=expiry_date
                        )
                        print(f"✅ Added expiry {expiry_month} for {stock_code}")
                    else:
                        return
                        print(f"⚠️ Expiry already exists for {stock_code} - {expiry_month}")

                except Stock.DoesNotExist:
                    print(f"❌ Stock not found: {row['stock_code']}")
                except ValueError as ve:
                    print(f"❌ Invalid date format in row {row}: {ve}")
                except Exception as e:
                    print(f"❌ Unexpected error processing row {row}: {e}")

    except FileNotFoundError:
        print(f"❌ File not found: {csv_path}")
    except Exception as e:
        print(f"❌ Could not open file: {e}")


if __name__ == "__main__":
    load_stocks_from_csv("static/unique.csv")
    populate_expiry_stock("static/expiry.csv")