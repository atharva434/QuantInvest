# views.py
from django.shortcuts import render, redirect, get_object_or_404
from .models import Expiry_Stock, Stock
# from .forms import Expiry_StockForm
import logging
from django.db import connection
from collections import namedtuple
import csv
from datetime import datetime
import ast
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from .serializers import ExpiryStockSerializer
from rest_framework import status

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

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_expiry_stock_api(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM get_expiry_stocks_with_stock_info()")
            desc = cursor.description
            columns = [col[0] for col in desc]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return Response({"items": data}, status=200)
    except Exception as e:
        logger.error(f"Error fetching expiry stocks via API: {e}")
        return Response({"error": "Failed to fetch expiry stocks"}, status=500)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_expiry_stock_api(request):
    data = request.data
    logger.info("API request to insert expiry stock: %s", data)

    required_fields = ['month', 'expiry_date']
    for field in required_fields:
        if field not in data:
            logger.warning("Missing field in request: %s", field)
            return Response({"error": f"Missing field: {field}"}, status=400)

    try:
        with connection.cursor() as cursor:
            if data.get('apply_to_all'):
                stocks = Stock.objects.all()
                for stock in stocks:
                    cursor.callproc('insert_expiry_stock', [
                        stock.id,
                        data['month'],
                        data['expiry_date']
                    ])
                logger.info("Inserted expiry stock for all stocks.")
            else:
                if 'stock' not in data:
                    return Response({"error": "Missing stock field"}, status=400)

                cursor.callproc('insert_expiry_stock', [
                    data['stock'],  # Stock ID
                    data['month'],
                    data['expiry_date']
                ])
                logger.info("Successfully inserted expiry stock for stock ID: %s", data['stock'])

        return Response({"message": "Expiry stock inserted successfully"}, status=201)

    except Exception as e:
        logger.error("Error inserting expiry stock via API: %s", str(e))
        return Response({"error": "Failed to insert expiry stock"}, status=500)
# def Expiry_Stock_add(request):
#     logger.info("Received request to add expiry stock.")
    
#     if request.method == 'POST':
#         form = Expiry_StockForm(request.POST)
#         if form.is_valid():
#             data = form.cleaned_data
#             logger.debug("Form data validated: %s", data)

#             try:
#                 with connection.cursor() as cursor:
#                     cursor.callproc('insert_expiry_stock', [
#                         data['stock'].id,
#                         data['month'],
#                         data['expiry_date']
#                     ])
#                 logger.info("Expiry stock successfully inserted for stock ID: %s", data['stock'].id)
#                 return redirect('stockexpiry_list')
#             except Exception as e:
#                 logger.error("Error while inserting expiry stock: %s", str(e))
#                 form.add_error(None, "Database error occurred.")
#     else:
#         form = Expiry_StockForm()
#         logger.debug("Rendering empty Expiry_StockForm.")

#     return render(request, 'stockexpiry_form.html', {'form': form, 'title': 'Add New'})

@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_expiry_stock_api(request, pk):
    data = request.data
    logger.info("API request to update expiry stock ID: %s", pk)

    required_fields = ['stock', 'month', 'expiry_date']
    for field in required_fields:
        if field not in data:
            logger.warning("Missing field in update request: %s", field)
            return Response({"error": f"Missing field: {field}"}, status=400)

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "CALL update_expiry_stock(%s, %s, %s, %s)",
                [pk, data['stock'], data['month'], data['expiry_date']]
            )
        logger.info("Successfully updated expiry stock via API. ID: %s", pk)
        return Response({"message": "Expiry stock updated successfully"}, status=200)

    except Exception as e:
        logger.error("Error updating expiry stock via API. ID: %s | Error: %s", pk, str(e))
        return Response({"error": "Failed to update expiry stock"}, status=500)

@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_expiry_stock_api(request, pk):
    logger.info("API request to delete Expiry_Stock ID: %s", pk)
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("CALL delete_expiry_stock(%s)", [pk])
        logger.info("Successfully deleted Expiry_Stock via API. ID: %s", pk)
        return Response({"message": "Expiry stock deleted successfully"}, status=204)
    except Exception as e:
        logger.error("Error deleting Expiry_Stock via API. ID: %s | Error: %s", pk, str(e))
        return Response({"error": "Failed to delete expiry stock"}, status=500)


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


from django.db import connection

def call_add_single_weekly_expiry(stock_code, expiry_date, month):
    with connection.cursor() as cursor:
        cursor.execute("SELECT add_single_weekly_expiry(%s, %s, %s);", [stock_code, expiry_date, month])


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def api_add_weekly_expiry(request):
    expiry_date = request.data.get('expiry_date')
    month = request.data.get('month')

    if not expiry_date or not month:
        return Response({'error': 'expiry_date and month are required.'}, status=400)

    stock_codes = ['NIFTY']

    try:
        for code in stock_codes:
            call_add_single_weekly_expiry(code, expiry_date, month)
    except Exception as e:
        print(e)
        return Response({'error': str(e)}, status=500)

    return Response({'message': 'Weekly expiry added successfully.'}, status=201)