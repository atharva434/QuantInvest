from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from .models import Stock
# from .forms import StockForm
from collections import namedtuple
import logging
from pathlib import Path
import csv
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import StockSerializer

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
    
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def stock_list(request):
    try:
        stocks = fetch_all_stocks()  # Assuming this returns a list of dicts or ORM queryset
        print(stocks)
        serialized_stocks = StockSerializer(stocks, many=True).data

        # If it returns ORM objects, serialize manually or via DRF serializers
        return Response({"stocks": serialized_stocks}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# def stock_create(request):
#     logger.info("Received request to create stock. Method: %s", request.method)

#     if request.method == 'POST':
#         form = StockForm(request.POST)
#         logger.debug("POST data received: %s", request.POST)

#         if form.is_valid():
#             data = form.cleaned_data
#             logger.info("Form is valid. Inserting stock: %s", data['stock_code'])

#             try:
#                 with connection.cursor() as cursor:
#                     cursor.callproc('insert_stock', [
#                         data['stock_code'],
#                         data['stock_name'],
#                         data['lot_size'],
#                         data['exchange_code'],
#                         data['stock_type'],
#                         data['fno_exchange_code']
#                     ])
#                 logger.info("Successfully inserted stock: %s", data['stock_code'])
#             except Exception as e:
#                 logger.error("Database error while inserting stock: %s | Error: %s", data['stock_code'], str(e))
#                 raise  # or handle gracefully

#             return redirect('stock_list')
#         else:
#             logger.warning("Form is invalid. Errors: %s", form.errors)
#     else:
#         form = StockForm()
#         logger.debug("Rendering empty form for stock creation.")

#     return render(request, 'stock_form.html', {'form': form, 'operation': 'Create'})

# def stock_update(request, pk):
#     logger.info("Received request to update stock with ID: %s", pk)

#     stock = get_object_or_404(Stock, pk=pk)
#     logger.debug("Fetched stock from DB: %s", stock)

#     if request.method == 'POST':
#         form = StockForm(request.POST, instance=stock)
#         logger.debug("POST data received for update: %s", request.POST)

#         if form.is_valid():
#             data = form.cleaned_data
#             logger.info("Form is valid. Updating stock: %s", data['stock_code'])

#             try:
#                 with connection.cursor() as cursor:
#                     cursor.callproc('update_stock', [
#                         stock.id,
#                         data['stock_code'],
#                         data['stock_name'],
#                         data['lot_size'],
#                         data['exchange_code'],
#                         data['stock_type'],
#                         data['fno_exchange_code']
#                     ])
#                 logger.info("Successfully updated stock: %s", data['stock_code'])
#             except Exception as e:
#                 logger.error("Error updating stock %s | Error: %s", stock.id, str(e))
#                 raise  # or handle it gracefully

#             return redirect('stock_list')
#         else:
#             logger.warning("Form is invalid for stock ID %s. Errors: %s", stock.id, form.errors)
#     else:
#         form = StockForm(instance=stock)
#         logger.debug("Rendering form for existing stock update. Stock ID: %s", stock.id)

#     return render(request, 'stock_form.html', {'form': form, 'operation': 'Update'})

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_stock_api(request, pk):
    data = request.data
    logger.info("API request to update stock ID %s with data: %s", pk, data)

    required_fields = [
        'stock_code', 'stock_name', 'lot_size',
        'exchange_code', 'stock_type', 'fno_exchange_code'
    ]

    for field in required_fields:
        if field not in data:
            logger.warning("Missing field in update request: %s", field)
            return Response({"error": f"Missing field: {field}"}, status=400)

    try:
        with connection.cursor() as cursor:
            cursor.callproc('update_stock', [
                pk,
                data['stock_code'],
                data['stock_name'],
                data['lot_size'],
                data['exchange_code'],
                data['stock_type'],
                data['fno_exchange_code']
            ])
        logger.info("Successfully updated stock via API: %s", data['stock_code'])
        return Response({"message": "Stock updated successfully"}, status=200)

    except Exception as e:
        logger.error("Error updating stock via API. ID: %s | Error: %s", pk, str(e))
        return Response({"error": "Failed to update stock"}, status=500)
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_stock_api(request):
    data = request.data
    logger.info("API request to insert stock: %s", data.get('stock_code'))

    required_fields = [
        'stock_code', 'stock_name', 'lot_size',
        'exchange_code', 'stock_type', 'fno_exchange_code'
    ]

    # Validate all required fields
    for field in required_fields:
        if field not in data:
            logger.warning("Missing field in request: %s", field)
            return Response({"error": f"Missing field: {field}"}, status=400)

    try:
        with connection.cursor() as cursor:
            cursor.callproc('insert_stock', [
                data['stock_code'],
                data['stock_name'],
                data['lot_size'],
                data['exchange_code'],
                data['stock_type'],
                data['fno_exchange_code']
            ])
        logger.info("Successfully inserted stock via API: %s", data['stock_code'])
        return Response({"message": "Stock inserted successfully"}, status=201)

    except Exception as e:
        logger.error("Error inserting stock via API: %s", str(e))
        return Response({"error": "Failed to insert stock"}, status=500)

@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def api_stock_delete(request, pk):
    try:
        stock = get_object_or_404(Stock, pk=pk)
        with connection.cursor() as cursor:
            cursor.callproc('delete_stock', [stock.id])
        return Response({"message": f"Stock {stock.stock_code} deleted successfully."}, status=204)
    except Exception as e:
        print('error', e)
        return Response({"error": str(e)}, status=500)



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