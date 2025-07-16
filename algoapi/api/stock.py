from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from .models import Stock
from .forms import StockForm
from collections import namedtuple
import logging
from pathlib import Path
import csv
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def fetch_all_stocks():
    logger.info("Starting fetch_all_stocks()")

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM get_all_stocks()")
            desc = cursor.description
            StockTuple = namedtuple("Stock", [col[0] for col in desc])
            results = [StockTuple(*row) for row in cursor.fetchall()]
        
        logger.info(f"Successfully fetched {len(results)} stocks.")
        return results

    except Exception as e:
        logger.error(f"Error in fetch_all_stocks(): {e}", exc_info=True)
        return []
    
from django.db import connection

def get_stock_info_by_id(stock_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_stock_info_by_id(%s);", [stock_id])
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

def get_stock_info_by_code(stock_code):
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
    

def stock_list(request):
    auth_token = request.session.get('auth_token')

    if not auth_token:
        return redirect("client_login")  # or handle unauthorized case

    try:
        headers = {
            "Authorization": f"Token {auth_token}"
        }
        response = requests.get(f"{settings.BACKEND_BASE_URL}/api/stocks/", headers=headers)

        if response.status_code == 200:
            data = response.json()
            print(data)
            return render(request, "stock_list.html", {"stocks": data["stocks"]})
        else:
            return render(request, "stock_list.html", {"error": "Failed to fetch stocks."})

    except Exception as e:
        return render(request, "stock_list.html", {"error": str(e)})

import logging
from django.shortcuts import render, redirect
from django.db import connection
from .forms import StockForm

logger = logging.getLogger(__name__)

def stock_create(request):
    logger.info("Received request to create stock. Method: %s", request.method)

    if request.method == 'POST':
        form = StockForm(request.POST)
        logger.debug("POST data received: %s", request.POST)

        if form.is_valid():
            data = form.cleaned_data
            logger.info("Form is valid. Sending stock to backend API: %s", data['stock_code'])

            auth_token = request.session.get('auth_token')
            if not auth_token:
                return redirect("client_login")

            headers = {
                'Authorization': f'Token {auth_token}'
            }

            try:
                response = requests.post(
                    f"{settings.BACKEND_BASE_URL}/api/stocks/create/",
                    headers=headers,
                    data=data
                )

                if response.status_code == 201:
                    logger.info("Stock creation successful via backend API.")
                    return redirect('stock_list')
                else:
                    logger.warning("API responded with error: %s", response.text)
                    form.add_error(None, response.json().get('error', 'Failed to create stock.'))

            except Exception as e:
                logger.error("Error during API call to create stock: %s", str(e))
                form.add_error(None, "Internal error while contacting backend.")

        else:
            logger.warning("Form is invalid. Errors: %s", form.errors)

    else:
        form = StockForm()
        logger.debug("Rendering empty form for stock creation.")

    return render(request, 'stock_form.html', {'form': form, 'operation': 'Create'})

def stock_update(request, pk):
    logger.info("Received request to update stock with ID: %s", pk)

    # Get existing data for pre-filling the form
    existing_stock = get_object_or_404(Stock, pk=pk)

    if request.method == 'POST':
        form = StockForm(request.POST)
        logger.debug("POST data received for update: %s", request.POST)

        if form.is_valid():
            data = form.cleaned_data
            logger.info("Form is valid. Sending update request to backend API.")

            auth_token = request.session.get('auth_token')
            if not auth_token:
                return redirect("client_login")

            headers = {
                "Authorization": f"Token {auth_token}"
            }

            try:
                response = requests.post(
                    f"{settings.BACKEND_BASE_URL}/api/stocks/update/{pk}/",
                    headers=headers,
                    data=data
                )

                if response.status_code == 200:
                    logger.info("Successfully updated stock via backend API.")
                    return redirect('stock_list')
                else:
                    logger.warning("API error: %s", response.text)
                    form.add_error(None, response.json().get("error", "Failed to update stock."))

            except Exception as e:
                logger.error("Exception during backend update call: %s", str(e))
                form.add_error(None, "Internal error while contacting backend.")
        else:
            logger.warning("Form invalid. Errors: %s", form.errors)

    else:
        form = StockForm(instance=existing_stock)
        logger.debug("Rendering pre-filled form for stock update.")

    return render(request, 'stock_form.html', {'form': form, 'operation': 'Update'})
def stock_delete(request, pk):
    auth_token = request.session.get('auth_token')

    if not auth_token:
        return redirect("client_login")

    if request.method == 'POST':
        try:
            headers = {
                "Authorization": f"Token {auth_token}"
            }
            response = requests.delete(f"{settings.BACKEND_BASE_URL}/api/stock-delete/{pk}/", headers=headers)

            if response.status_code in [200, 204]:
                return redirect("stock_list")
            else:
                error_msg = response.json().get("error", "Failed to delete stock.")
                return render(request, "stock_confirm_delete.html", {"error": error_msg, "stock_id": pk})

        except Exception as e:
            return render(request, "stock_confirm_delete.html", {"error": str(e), "stock_id": pk})

    # GET request → show confirmation page
    return render(request, "stock_confirm_delete.html", {"stock_id": pk})


def load_stocks_from_csv(csv_path: str):
    csv_file = Path(csv_path)
    
    if not csv_file.exists():
        print(f"File not found: {csv_path}")
        return

    with open(csv_file, newline='') as file:
        reader = csv.DictReader(file)

        for row in reader:
            try:
                # Parse expiry tuple ('APR-2025', datetime.date(2025, 4, 24))

                stock = Stock(
                    stock_code=row['stock_code'],
                    stock_name=row['stock_name'],
                    lot_size=int(row['lot_size']),
                    exchange_code=row['exchange_code'],
                    stock_type=row['stock_type'],
                    fno_exchange_code=row['fno_exchange_code'],
                )
                stock.save()
                print(f"✅ Saved stock: {stock.stock_code}")

            except Exception as e:
                print(f"❌ Error on row {row}: {e}")

def fetch_future_expiry_dates(stock_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT expiry_date
            FROM api_expiry_stock
            WHERE stock_id = %s AND expiry_date >= CURRENT_DATE
            ORDER BY expiry_date ASC
        """, [stock_id])
        return [row[0] for row in cursor.fetchall()]