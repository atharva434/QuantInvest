# views.py
from django.shortcuts import render, redirect, get_object_or_404
from .models import Expiry_Stock, Stock
from .forms import Expiry_StockForm, WeeklyExpiryForm
import logging
from django.db import connection
from collections import namedtuple
import csv
from datetime import datetime
import ast
import requests
from django.contrib import messages
from datetime import datetime, timedelta
from django.conf import settings


logger = logging.getLogger(__name__)

def fetch_stock_info():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM get_expiry_stocks_with_stock_info()")
            desc = cursor.description
            ExpiryStockTuple = namedtuple("ExpiryStock", [col[0] for col in desc])
            items = [ExpiryStockTuple(*row) for row in cursor.fetchall()]
            logger.info("Fetched Expiry_Stock list.")
    except Exception as e:
        logger.error(f"Error fetching Expiry_Stock list : {e}")
        items = []
    # print(items)
    return items


def get_stock_expiry_id(stock_code, expiry_date):
    """
    Call the stored procedure to get the stock_expiry_id based on stock_code and expiry_date.
    :param stock_code: The stock code (e.g., 'NIFTY')
    :param expiry_date: The expiry date (e.g., '2025-02-06')
    :return: The stock_expiry_id or None if not found
    """
    with connection.cursor() as cursor:
        # Execute the stored procedure and fetch the result
        cursor.execute("SELECT get_expiry_stock_id(%s, %s);", [stock_code, expiry_date])
        
        # Fetch the result
        result = cursor.fetchone()
        
        # If a result is found, return the stock_expiry_id, else return None
        return result[0] if result else None

def Expiry_Stock_list(request):
    auth_token = request.session.get('auth_token')
    if not auth_token:
        return redirect("client_login")

    headers = {
        "Authorization": f"Token {auth_token}"
    }

    try:
        response = requests.get(f"{settings.BACKEND_BASE_URL}/api/expiry-stocks/", headers=headers)

        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
        else:
            logger.warning(f"Backend returned status {response.status_code} for expiry stock list.")
            items = []
    except Exception as e:
        logger.error(f"Exception while calling expiry stock API: {e}")
        items = []

    return render(request, 'stockexpiry_list.html', {'items': items})


def Expiry_Stock_add(request):
    logger.info("Received request to add expiry stock.")

    auth_token = request.session.get('auth_token')
    if not auth_token:
        return redirect("client_login")

    if request.method == 'POST':
        form = Expiry_StockForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            logger.debug("Form data validated: %s", data)

            payload = {
                "month": data['month'],
                "expiry_date": str(data['expiry_date']),
            }

            if request.POST.get('apply_to_all') == 'on':
                payload["apply_to_all"] = True
            else:
                payload["stock"] = data['stock'].id

            headers = {
                "Authorization": f"Token {auth_token}",
                "Content-Type": "application/json"
            }

            try:
                response = requests.post(
                    f"{settings.BACKEND_BASE_URL}/api/expiry-stocks-add/",
                    json=payload,
                    headers=headers
                )

                if response.status_code == 201:
                    messages.success(request, "Expiry stock inserted successfully.")
                    return render(request, 'stockexpiry_form.html', {'form': form, 'title': 'Add New'})
                else:
                    logger.error("API insert failed: %s", response.text)
                    form.add_error(None, "Failed to insert expiry stock via API.")
            except Exception as e:
                logger.error("Error calling expiry stock insert API: %s", str(e))
                form.add_error(None, "Internal error occurred.")
    else:
        form = Expiry_StockForm()
        logger.debug("Rendering empty Expiry_StockForm.")

    return render(request, 'stockexpiry_form.html', {'form': form, 'title': 'Add New'})
def Expiry_Stock_update(request, pk):
    instance = get_object_or_404(Expiry_Stock, pk=pk)
    auth_token = request.session.get('auth_token')

    if not auth_token:
        return redirect('client_login')

    if request.method == 'POST':
        form = Expiry_StockForm(request.POST, instance=instance)
        if form.is_valid():
            data = form.cleaned_data
            payload = {
                "stock": data['stock'].id,
                "month": data['month'],
                "expiry_date": str(data['expiry_date'])  # Convert to ISO format
            }

            headers = {
                "Authorization": f"Token {auth_token}"
            }

            try:
                response = requests.put(
                    f"{settings.BACKEND_BASE_URL}/api/expiry-stocks-update/{pk}/",
                    json=payload,
                    headers=headers
                )

                if response.status_code == 200:
                    logger.info("Expiry stock successfully updated via API. ID: %s", pk)
                    return redirect('stockexpiry_list')
                else:
                    logger.error("API update failed: %s", response.text)
                    form.add_error(None, "Failed to update expiry stock via API.")
            except Exception as e:
                logger.error("Error calling expiry stock update API: %s", str(e))
                form.add_error(None, "Internal error occurred.")
    else:
        form = Expiry_StockForm(instance=instance)

    return render(request, 'stockexpiry_form.html', {'form': form, 'title': 'Update'})

def Expiry_Stock_delete(request, pk):
    instance = get_object_or_404(Expiry_Stock, pk=pk)
    auth_token = request.session.get('auth_token')

    if not auth_token:
        return redirect('client_login')

    if request.method == 'POST':
        headers = {
            "Authorization": f"Token {auth_token}"
        }

        try:
            response = requests.delete(
                f"{settings.BACKEND_BASE_URL}/api/expiry-stocks-delete/{pk}/",
                headers=headers
            )

            if response.status_code in [200, 204]:
                logger.info("Successfully deleted Expiry_Stock via API. ID: %s", pk)
                return redirect('stockexpiry_list')
            else:
                logger.error("API deletion failed: %s", response.text)
        except Exception as e:
            logger.error("Error calling delete Expiry_Stock API: %s", str(e))

    return render(request, 'stockexpiry_confirm_delete.html', {'item': instance})


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



def add_weekly_expiry(request):
    auth_token = request.session.get('auth_token')

    if not auth_token:
        return redirect('client_login')

    if request.method == 'POST':
        form = WeeklyExpiryForm(request.POST)
        if form.is_valid():
            expiry_date = form.cleaned_data['expiry_date']
            month = form.cleaned_data['month']

            headers = {
                'Authorization': f'Token {auth_token}'
            }

            payload = {
                'expiry_date': expiry_date.strftime('%Y-%m-%d'),
                'month': month
            }

            try:
                response = requests.post(
                    f"{settings.BACKEND_BASE_URL}/api/expiry-stocks-weekly/",
                    json=payload,
                    headers=headers
                )

                if response.status_code == 201:
                    messages.success(request, response.json().get('message'))
                else:
                    messages.error(request, f"API Error: {response.json().get('error', 'Unknown error')}")
            except requests.exceptions.RequestException:
                messages.error(request, "Unable to reach backend API.")

            return redirect('stockexpiry_list')
    else:
        form = WeeklyExpiryForm()

    return render(request, 'weekly_expiry_form.html', {'form': form, 'title': 'Add Weekly Expiry'})