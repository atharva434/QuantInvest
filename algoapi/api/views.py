from django.shortcuts import render,redirect
from django.views.decorators.csrf import csrf_exempt
from .yieldcalculator import *
from django.contrib.auth.decorators import login_required
from django.db import connection
import pandas as pd
from api import stock,stockexpiry
from api import stock, stockprice, option_chain, transactions, open_positions
from django.http import JsonResponse
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import logging
from .decorators import block_admins
from datetime import date, timedelta
from django.urls import reverse
from datetime import datetime
from django.db import transaction
from django.contrib import messages
from api import load_csv_daily
from .utils import update_progress, get_progress, get_atm_per
import re
import threading
import os
from django.conf import settings
logger = logging.getLogger(__name__)
from django.http import HttpResponse
from io import BytesIO
from decouple import config
import requests

# def process_selected_stocks(request):
#     if request.method == 'POST':
#         user = request.user
#         try:
#             session_token = request.session['session_token']
#         except:
#             return redirect("client_login")
#         try:
#             breeze = get_breeze_for_user(user, session_token)
#         except Exception as e:
#             return redirect("client_login")

#         try:
#             total = int(request.POST.get('total_items', 0))
#             print(total)
#             for i in range(1, total + 1):
#                 if request.POST.get(f'selected_{i}') is not None:
#                     stock_code = request.POST.get(f'stock_code_{i}')
#                     expiry_date = request.POST.get(f'expiry_date_{i}')
#                     stock_id = request.POST.get(f"stock_id_{i}")
#                     right = request.POST.get(f'right_{i}')
#                     print(stock_code)
#                     stock_info = stock.get_stock_info_by_code(stock_code)
#                     stock_id = stock_info["id"]
#                     ltp = stockprice.save_stock_price(breeze, stock_code, stock_id, stock_info["stock_name"])
#                     print(ltp)
#                     option_chain.save_optionchain(breeze, stock_info, expiry_date, ltp, right)

#             return redirect("full_table")

#         except Exception as e:
#             logger.error(f"Error processing selected stocks: {str(e)}", exc_info=True)
#             return JsonResponse({'status': 'error', 'message': 'An error occurred while processing selected stocks'})

#     return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
def process_selected_stocks(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

    token = request.session.get("auth_token")
    session_token = request.session.get("session_token")

    if not token or not session_token:
        return redirect("client_login")

    try:
        total = int(request.POST.get('total_items', 0))
        print(total)
        payload = {'total_items': total}
        for i in range(1, total + 1):
            if request.POST.get(f'selected_{i}') is not None:
                payload[f'selected_{i}'] = True
                payload[f'stock_code_{i}'] = request.POST.get(f'stock_code_{i}')
                payload[f'expiry_date_{i}'] = request.POST.get(f'expiry_date_{i}')
                payload[f'right_{i}'] = request.POST.get(f'right_{i}')

        response = requests.post(
            settings.BACKEND_BASE_URL + "/api/process-selected-stocks/",
            headers={"Authorization": f"Token {token}"},
            params={"session_token": session_token},
            data=payload
        )

        if response.status_code == 200:
            return redirect("full_table")
        else:
            return JsonResponse({'status': 'error', 'message': 'Backend error'}, status=500)

    except Exception as e:
        logger.error(f"Frontend error: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Frontend processing error'})
@csrf_exempt
def set_session_token(request):
    logger.info(f"Received {request.method} request to set session token")

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_token = data.get("session_token")
            logger.info(f"Parsed session token from request: {session_token}")

            if request.user.is_authenticated:
                request.session['session_token'] = session_token
                logger.info(f"Session token set for user: {request.user}")
                return JsonResponse({"status": "ok"})
            else:
                logger.warning("Unauthenticated user attempted to set session token")
                return JsonResponse({"status": "unauthenticated"})
        except Exception as e:
            logger.error(f"Failed to set session token: {e}", exc_info=True)
            return JsonResponse({"status": "error"})
    
    logger.warning("Invalid request method used for setting session token")
    return JsonResponse({"status": "error", "message": "Invalid request method"})

@login_required(login_url='/client_login')
def home(request):
    stock_data = stockexpiry.fetch_stock_info()
    today = date.today()

    # Filter out stocks where expiry_date is today or in future
    filtered_stock_data = [
        stock for stock in stock_data
        if hasattr(stock, 'expiry_date') and stock.expiry_date and stock.expiry_date >= today
    ]

    return render(request, "home.html", {"stock_data": filtered_stock_data})

# @login_required(login_url='/client_login')

def full_table(request):
    token = request.session.get("auth_token")
    session_token = request.session.get("session_token")

    if not token or not session_token:
        return redirect("client_login")

    try:
        response = requests.get(
            settings.BACKEND_BASE_URL + "/api/get-full-table/",
            headers={"Authorization": f"Token {token}"},
            params={"session_token": session_token}
        )
        if response.status_code == 200:
            data = response.json()
            option_data_grouped = data.get("option_data_grouped", {})
            ltp_missing = data.get("ltp_missing", [])
        else:
            option_data_grouped = {}
            ltp_missing = []

    except Exception as e:
        logger.error(f"Error fetching full table: {e}", exc_info=True)
        option_data_grouped = {}
        ltp_missing = []

    sorted_option_data_grouped = sorted(option_data_grouped.items(), key=lambda x: x[0])
    try:
        response = requests.get(
            settings.BACKEND_BASE_URL + "/api/get-valid-expiries/",
            headers={"Authorization": f"Token {token}"},
            params={"session_token": session_token}
        )
        if response.status_code == 200:
            data = response.json()
            valid_expiries = data.get("expiry_dates", [])
        else:
            valid_expiries = []

    except Exception as e:
        logger.error(f"Error fetching valid expiries: {e}", exc_info=True)
        valid_expiries = []

    return render(request, 'option_chain.html', {
        'option_data_grouped': sorted_option_data_grouped,
        'option_data_grouped_json': json.dumps(option_data_grouped, default=str),
        'ltp_missing': ltp_missing,
        'auth_token': token,
        'session_token': session_token,
         'valid_expiries': valid_expiries,
        'backend_url': settings.BACKEND_JS_URL
    })
import logging

logger = logging.getLogger(__name__)

def calculate_yield(request):
    if request.method == 'POST':
        total = int(request.POST.get('total_items', 0))
        print(total)
        print(request.POST)
        logger.info(f"Total items received: {total}")
#         results = []
#         user = request.user
#         session_token = request.session.get('session_token')
        
#         if not session_token:
#             logger.warning("Session token missing or expired.")
#             return JsonResponse({
#                 'status': 'session_invalid',
#                 'message': 'Session expired or invalid. Click the link below to log in.',
#                 'login_url': '/client_login'
#             })

#         try:
#             breeze = get_breeze_for_user(user, session_token)
#             logger.info(f"Breeze session created for user: {user}")
#         except Exception as e:
#             logger.error("Breeze authentication failed", exc_info=True)
#             return JsonResponse({
#                 'status': 'error',
#                 'message': 'Breeze authentication failed.'
#             })

#         for i in range(1, total + 1):
#             if request.POST.get(f'selected_{i}'):
#                 try:
#                     stock_code = request.POST.get(f'stock_code_{i}')
#                     expiry_date = request.POST.get(f'expiry_date_{i}')
#                     right = request.POST.get(f'right_{i}')
#                     strike_price = float(request.POST.get(f'strike_price_{i}', 0))
#                     lot_size = float(request.POST.get(f'lot_size_{i}', 0))
#                     lots = int(request.POST.get(f'lots_{i}', 1))

#                     logger.info(f"Processing stock: {stock_code}, expiry: {expiry_date}, strike: {strike_price}")

#                     option_chain = get_option_chain_for_strike(
#                         breeze=breeze, 
#                         stock_code=stock_code, 
#                         right=right, 
#                         strike_price=strike_price, 
#                         expiry_date=expiry_date
#                     )
#                     ltp = option_chain[0]["ltp"]
#                     margin = get_margin(
#                         breeze=breeze, 
#                         stockcode=stock_code, 
#                         strikeprice=strike_price, 
#                         ltp=ltp, 
#                         quantity=lot_size * lots, 
#                         expiry_date=expiry_date, 
#                         right=right,
#                     )

#                     try:
#                         current_price = get_ltp(breeze=breeze, stock_code=stock_code)["ltp"]
#                     except Exception as e:
#                         logger.warning(f"Could not fetch LTP for {stock_code}: {e}")
#                         current_price = 0

#                     yield_value = (ltp * lot_size * lots) / margin * 100 if margin else 0

#                     logger.info(f"Yield for {stock_code}: {yield_value:.2f}%")

#                     results.append({
#                         "stock_code": stock_code,
#                         "right": right,
#                         "yield_value": yield_value,
#                         "ltp": ltp,
#                         "margin": margin,
#                         "cmp": current_price
#                     })
#                 except Exception as e:
#                     logger.error(f"Error processing item {i}: {str(e)}", exc_info=True)
#         print(results)
#         return JsonResponse({"status": "success", "data": results})
#     else:
#         logger.warning("Invalid request method for calculate_yield.")
#         return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

# def calculate_yield(request):
#     if request.method != 'POST':
#         return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

#     token = request.session.get("auth_token")
#     session_token = request.session.get("session_token")

#     if not token or not session_token:
#         return JsonResponse({
#             'status': 'session_invalid',
#             'message': 'Session expired or invalid.',
#             'login_url': '/client_login'
#         })

#     try:
#         total = int(request.POST.get('total_items', 0))
#         print(request.POST)
#         payload = {'total_items': total}

#         for i in range(1, total + 1):
#             if request.POST.get(f'selected_{i}'):
#                 payload[f'selected_{i}'] = True
#                 payload[f'stock_code_{i}'] = request.POST.get(f'stock_code_{i}')
#                 payload[f'expiry_date_{i}'] = request.POST.get(f'expiry_date_{i}')
#                 payload[f'right_{i}'] = request.POST.get(f'right_{i}')
#                 payload[f'strike_price_{i}'] = request.POST.get(f'strike_price_{i}')
#                 payload[f'lot_size_{i}'] = request.POST.get(f'lot_size_{i}')
#                 payload[f'lots_{i}'] = request.POST.get(f'lots_{i}')

#         response = requests.post(
#             settings.BACKEND_BASE_URL + "/api/calculate-yield/",
#             headers={"Authorization": f"Token {token}"},
#             params={"session_token": session_token},
#             data=payload
#         )
#         print(response.json())

#         return JsonResponse(response.json(), status=response.status_code)

#     except Exception as e:
#         logger.error(f"Frontend error in calculate_yield: {e}", exc_info=True)
#         return JsonResponse({'status': 'error', 'message': 'Error occurred while preparing request'})


def buy_sell_conf(request):
    token = request.session.get("auth_token")
    session_token = request.session.get("session_token")
    if not token or not session_token:
        return redirect("client_login")

    selected_orders = request.session.get('selected_orders', [])
    # print(selected_orders)
    payload = {'total_items': len(selected_orders)}
    # selected_orders["strike_price"] = float(selected_orders["strike_price"])
    
    for i, stock in enumerate(selected_orders):
        payload[f'stock_code_{i}'] = stock["stock_code"]
        payload[f'expiry_date_{i}'] = stock["expiry_date"]
        payload[f'right_{i}'] = stock["right"]

    response = requests.post(
        settings.BACKEND_BASE_URL + "/api/get_option_chain/",
        headers={"Authorization": f"Token {token}"},
        params={"session_token": session_token},
        data=payload
    )
    strike_data_per_order = []
    if response.status_code == 200:
        updated_orders = response.json().get("updated_orders", [])
        for i, updated in enumerate(updated_orders):
            # Only update keys that are present in the updated dict
            for key, value in updated.items():
                selected_orders[i][key] = value
            selected_orders[i]["strike_price"] = float(selected_orders[i]["strike_price"])

            strike_prices = updated.get("strike_prices", [])
            order_prices = updated.get("order_prices", [])
            best_offer_prices = updated.get("best_offer_prices", [])
            best_bid_prices = updated.get("best_bid_prices", [])

            # Build the map: {strike: {order_price, best_offer_price, best_bid_price}}
            
            strike_map = {
                str(sp): {
                    "order_price": op,
                    "best_offer_price": bop,
                    "best_bid_price": bbp
                }
                for sp, op, bop, bbp in zip(strike_prices, order_prices, best_offer_prices, best_bid_prices)
            }

            strike_data_per_order.append(strike_map)
    request.session['selected_orders'] = selected_orders

    # print(selected_orders)

    return render(request, 'buy_sell_conf.html', {'selected_orders': selected_orders, 'auth_token': token,
        'session_token': session_token,
        'strike_data_json': json.dumps(strike_data_per_order),
        'backend_url': settings.BACKEND_JS_URL })

@csrf_exempt
def place_order(request):
    if request.method == 'POST':
        logger.info("Received POST request for placing orders")

        session_token = request.session.get('session_token')
        breeze = get_breeze_for_user(request.user, session_token)
        total_rows = int(request.POST.get("total_rows", 0))

        results = []

        row_indices = sorted({
            int(re.search(r'stock_code_(\d+)', key).group(1))
            for key in request.POST.keys()
            if re.match(r'stock_code_\d+', key)
        })

        logger.info(f"Identified rows to process: {row_indices}")

        for i in row_indices:
            stock_code = request.POST.get(f"stock_code_{i}")
            if not stock_code:
                continue

            logger.info(f"Processing order for row {i} and stock_code {stock_code}")

            row_result = {
                "row": i,
                "stock_code": request.POST.get(f"stock_code_{i}"),
                "status": "not_attempted",
                "error": "",
                "order_ids": [],
                "quantities": []
            }

            try:
                with transaction.atomic():
                    stock_code = row_result["stock_code"]
                    product = "options"
                    exchange_code = "nfo"
                    action = request.POST.get(f"action_{i}")
                    order_type = request.POST.get(f"order_type_{i}")
                    stop_loss = request.POST.get(f"stoploss_{i}")
                    stop_loss = int(stop_loss) if stop_loss else 0

                    quantity = int(request.POST.get(f"quantity_{i}"))
                    order_price = request.POST.get(f"order_price_{i}")
                    order_price = float(order_price) if order_price else None

                    expiry_date = request.POST.get(f"expiry_date_{i}")
                    parsed_date = datetime.strptime(expiry_date, '%B %d, %Y')
                    expiry_date = parsed_date.strftime('%Y-%m-%d')

                    right = request.POST.get(f"right_{i}")
                    strike_price = request.POST.get(f"strike_price_{i}")
                    strike_price = float(strike_price) if strike_price else 0.0

                    lot_size = int(request.POST.get(f"lot_size_{i}"))

                    with open("api/order_limit.json") as f:
                        order_limit = json.load(f)

                    if stock_code in order_limit:
                        logger.info(f"Stock {stock_code} has an order limit. Applying max_qty_limit: {order_limit[stock_code]}")
                        order_ids = buy_sell(
                            breeze, stock_code, exchange_code, action, order_type,
                            stop_loss, quantity, order_price,
                            expiry_date, right, strike_price, lot_size,
                            split_orders=True,
                            max_qty_limit=order_limit[stock_code]
                        )
                    else:
                        logger.info(f"Stock {stock_code} has no order limit. Proceeding without quantity split.")
                        order_ids = buy_sell(
                            breeze, stock_code, exchange_code, action, order_type,
                            stop_loss, quantity, order_price,
                            expiry_date, right, strike_price, lot_size
                        )

                    success_flag = False
                    for result in order_ids:
                        if result["status"] == "success":
                            transactions.place_order_with_sp(
                                stock_code, exchange_code, expiry_date, right,
                                strike_price, result["order_id"], action, order_type,
                                0, result["quantity"]
                            )
                            row_result["order_ids"].append(result["order_id"])
                            row_result["quantities"].append(result["quantity"])
                            success_flag = True
                        else:
                            row_result["error"] = result.get("error", "Unknown error")

                    if success_flag:
                        logger.info(f"Successfully placed orders for row {i}, stock_code {stock_code}")
                        row_result["status"] = "success"
                    else:
                        logger.warning(f"Order placement failed for row {i}, stock_code {stock_code}. Error: {row_result['error']}")
                        row_result["status"] = "failed"

            except Exception as e:
                logger.error(f"Exception while placing order for row {i}, stock_code {stock_code}: {e}", exc_info=True)
                row_result["status"] = "failed"
                row_result["error"] = str(e)

            results.append(row_result)

        logger.info(f"Order placement results: {results}")
        return JsonResponse({'success': True, 'results': results})

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

def place_orders(request):
    logger.info(f"Request method: {request.method}")
    token = request.session.get("auth_token")
    session_token = request.session.get("session_token")

    if not token or not session_token:
        return redirect("client_login")

    if request.method == 'POST':
        try:
            # Parse incoming JSON data
            data = json.loads(request.body)
            logger.info(f"Received data: {data}")

            selected_orders = data.get('orders', [])
            if not selected_orders:
                logger.warning("No orders selected.")
                return JsonResponse({'status': 'error', 'message': 'No orders selected.'})

            enriched_orders = []

            for order in selected_orders:
                stock_code = order.get('stock_code')
                right = order.get('right')
                logger.info(f"Processing order: stock_code={stock_code}, right={right}")
                response = requests.get(
                            settings.BACKEND_BASE_URL + "/api/strikes/",
                            headers={"Authorization": f"Token {token}"},
                            params={"session_token": session_token, "stock_code":stock_code, "right":right}
                        )
                strike_prices=[]
                if response.status_code == 200:
                    data = response.json()
                    strike_prices=data["strikes"]

                # strike_prices = option_chain.get_strikes_by_stock_and_right(stock_code, right)
                strike_prices = sorted(set(strike_prices))

                order['strike_prices'] = strike_prices
                order['order_price'] = order.get('ltp')
                enriched_orders.append(order)

            request.session['selected_orders'] = enriched_orders
            logger.info("Orders successfully enriched and stored in session.")

            return JsonResponse({
                'status': 'ok',
                'redirect_url': reverse('buy_sell_conf')
            })

        except Exception as e:
            logger.error(f"Error placing orders: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': f'Error placing orders: {str(e)}'})

    else:
        logger.warning("Invalid request method.")
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})
    
# def show_open_positions(request):
#     # load_csv_daily.insert_from_excel("api/Historical_Data_v2.xlsx")
#     session_token = request.session.get('session_token')
#     breeze = get_breeze_for_user(request.user, session_token)
    

#     # Get open positions from Breeze (ICICI)
#     positions = open_positions.get_open_positions(breeze)

#     if not positions:
#         return render(request, 'open_positions.html', {'grouped_data': []})

#     # Convert to DataFrame
#     df = pd.DataFrame(positions)
#     df = df[df["exchange_code"]=="NFO"]
#     print(df)

#     # Keep only open positions (quantity > 0)
#     df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
#     df = df[df["quantity"] > 0]
#     # Clean and convert required numeric columns
#     df["ltp"] = pd.to_numeric(df["ltp"], errors="coerce")
#     df["average_price"] = pd.to_numeric(df["average_price"], errors="coerce")
#     df["pnl"] = pd.to_numeric(df.get("pnl", None), errors="coerce")

#     # If pnl not given, compute it
#     if df["pnl"].isnull().all():
#         df["PL"] = df.apply(
#             lambda row: (row["average_price"] - row["ltp"]) * row["quantity"]
#             if row["action"].strip().lower() == "sell"
#             else (row["ltp"] - row["average_price"]) * row["quantity"],
#             axis=1
#         )
#         df["PL"] = df["PL"].round(2)
#     else:
#         df["PL"] = df["pnl"]

#     # Rename for clarity in template
#     df.rename(columns={
#         "stock_code": "StockCode",
#         "strike_price": "Strike",
#         "right": "Right",
#         "action": "Action",
#         "quantity": "Qty",
#         "average_price": "AvgCost",
#         "ltp": "LTP",
#         "expiry_date": "Expiry"
#     }, inplace=True)

#     # Grouping by stock
#     grouped_data = []
#     for stock_code, group in df.groupby("StockCode"):
#         group_data = group.copy()

#         total_row = {
#             "StockCode": stock_code,
#             "Contract": "Total",
#             "Qty": group_data["Qty"].sum(),
#             "AvgCost": "",
#             "LTP": "",
#             "PL": group_data["PL"].sum()
#         }

#         grouped_data.append({
#             "stock_code": stock_code,
#             "rows": group_data.to_dict(orient="records"),
#             "total": total_row
#         })
    

#     return render(request, 'open_positions.html', {'grouped_data': grouped_data})


def show_open_positions(request):
    token = request.session.get("auth_token")
    session_token = request.session.get("session_token")

    if not token or not session_token:
        return redirect("client_login")

    try:
        response = requests.get(
            settings.BACKEND_BASE_URL + "/api/get-open-positions/",
            headers={"Authorization": f"Token {token}"},
            params={"session_token": session_token}
        )

        if response.status_code == 200:
            data = response.json()
            return render(request, "open_positions.html", {"grouped_data": data["grouped_data"]})
        else:
            return render(request, "open_positions.html", {"grouped_data": [], "error": "Failed to fetch data"})

    except Exception as e:
        return render(request, "open_positions.html", {"grouped_data": [], "error": str(e)})
    

# def trade_pnl_summary(request):
#     logger.info("Starting P&L summary generation")

#     session_token = request.session.get('session_token')
#     breeze = get_breeze_for_user(request.user, session_token)

#     try:
#         with open("api/index_scripts.json") as f:
#             index_scripts = json.load(f)
#         indexes = index_scripts["Index"]
#         logger.info("Loaded index scripts successfully")
#     except Exception as e:
#         logger.error(f"Error loading index_scripts.json: {e}", exc_info=True)
#         indexes = []

#     try:
#         positions = open_positions.get_open_positions(breeze)
#         df = pd.DataFrame(positions)
#         df = df[df["exchange_code"]=="NFO"]
#         logger.info(f"Fetched {len(df)} open positions")
#     except Exception as e:
#         logger.error(f"Error fetching open positions: {e}", exc_info=True)
#         df = pd.DataFrame()

#     try:
#         df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
#         df["ltp"] = pd.to_numeric(df["ltp"], errors="coerce")
#         df["average_price"] = pd.to_numeric(df["average_price"], errors="coerce")
#         df["pnl"] = pd.to_numeric(df.get("pnl", None), errors="coerce")

#         df["realizedpl"] = df.apply(
#             lambda row: row["average_price"] * row["quantity"]
#             if row["action"].strip().lower() == "sell"
#             else row["average_price"] * row["quantity"] * (-1),
#             axis=1
#         )
#         df["realizedpl"] = df["realizedpl"].round(2)

#         if df["pnl"].isnull().all():
#             logger.info("No pnl column available — using fallback computation")
#             df["PL"] = df.apply(
#                 lambda row: row["ltp"] * row["quantity"] * (-1)
#                 if row["action"].strip().lower() == "sell"
#                 else row["ltp"] * row["quantity"],
#                 axis=1
#             )
#             df["PL"] = df["PL"].round(2)
#         else:
#             df["PL"] = df["pnl"]
#             df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce")

#         df["strike_price"] = pd.to_numeric(df["strike_price"], errors="coerce")
#         df["is_index"] = df["stock_code"].isin(indexes).astype(int)
#         df["right_order"] = df["right"].str.lower().map({"call": 0, "put": 1})
#         df["action_order"] = df["action"].str.lower().map({"buy": 0, "sell": 1})
#         df = df.sort_values(
#             by=["is_index", "stock_code", "expiry_date", "right_order", "strike_price", "action_order"],
#             ascending=[False, True, True, True, True, True]
#         )
#     except Exception as e:
#         logger.error(f"Error processing open positions data: {e}", exc_info=True)
#         df = pd.DataFrame()

#     # Fetch holdings
#     try:
#         holdings = open_positions.get_portfolio_holdings(breeze)
#         if holdings:
#             df_holdings = pd.DataFrame(holdings)
#             logger.info(f"Fetched {len(df_holdings)} portfolio holdings")

#             df_holdings["stock_code"] = df_holdings["stock_code"].str.strip()
#             df_holdings["quantity"] = pd.to_numeric(df_holdings["quantity"], errors="coerce").fillna(0)
#             df_holdings["average_price"] = pd.to_numeric(df_holdings["average_price"], errors="coerce").fillna(0)
#             df_holdings["ltp"] = pd.to_numeric(df_holdings["current_market_price"], errors="coerce").fillna(0)
#             df_holdings["realizedpl"] = pd.to_numeric(df_holdings["realized_profit"], errors="coerce").fillna(0)
#             df_holdings["PL"] = pd.to_numeric(df_holdings["unrealized_profit"], errors="coerce").fillna(0)

#             df_holdings["action"] = df_holdings.get("action", "Buy")
#             df_holdings["right"] = df_holdings.get("right", "")
#             df_holdings["expiry_date"] = pd.to_datetime(df_holdings.get("expiry_date", None), errors="coerce")
#             df_holdings["strike_price"] = pd.to_numeric(df_holdings.get("strike_price", None), errors="coerce")

#             df_holdings["source"] = "Holding"

#             df_holdings = df_holdings[[
#                 "stock_code", "quantity", "average_price", "ltp", "realizedpl", "PL",
#                 "action", "right", "expiry_date", "strike_price", "source", "product_type"
#             ]]
#         else:
#             df_holdings = pd.DataFrame()
#             logger.info("No holdings data returned")
#     except Exception as e:
#         logger.error(f"Error processing portfolio holdings: {e}", exc_info=True)
#         df_holdings = pd.DataFrame()

#     try:
#         df_combined = pd.concat([df, df_holdings], ignore_index=True)
#         df_dict = df_combined.to_dict(orient='records')

#         total_realized = sum(row['realizedpl'] for row in df_dict if row.get('realizedpl') is not None)
#         total_unrealized = sum(row['PL'] for row in df_dict if row.get('PL') is not None)
#         total_pnl = total_realized + total_unrealized

#         logger.info(f"Total Realized PnL: {total_realized}, Unrealized: {total_unrealized}, Combined: {total_pnl}")
#     except Exception as e:
#         logger.error(f"Error combining or calculating PnL data: {e}", exc_info=True)
#         df_dict, total_realized, total_unrealized, total_pnl = [], 0, 0, 0

#     return render(request, 'pnl_summary.html', {
#         'df': df_dict,
#         'total_realized': total_realized,
#         'total_unrealized': total_unrealized,
#         'total_pnl': total_pnl,
#     })

def trade_pnl_summary(request):
    token = request.session.get("auth_token")
    session_token = request.session.get("session_token")

    if not token or not session_token:
        return redirect("client_login")

    try:
        response = requests.get(
            settings.BACKEND_BASE_URL + "/api/get-pnl-summary/",
            headers={"Authorization": f"Token {token}"},
            params={"session_token": session_token}
        )
        print(response.json())
        if response.status_code == 200:
            data = response.json()
            df_dict = data.get("df", [])
            total_realized = data.get("total_realized", 0)
            total_unrealized = data.get("total_unrealized", 0)
            total_pnl = data.get("total_pnl", 0)
        else:
            logger.error(f"Backend PnL fetch failed: {response.status_code} - {response.text}")
            df_dict, total_realized, total_unrealized, total_pnl = [], 0, 0, 0

    except Exception as e:
        logger.error(f"Error fetching PnL summary: {e}", exc_info=True)
        df_dict, total_realized, total_unrealized, total_pnl = [], 0, 0, 0

    return render(request, 'pnl_summary.html', {
        'df': df_dict,
        'total_realized': total_realized,
        'total_unrealized': total_unrealized,
        'total_pnl': total_pnl,
    })



def analysis_view(request):
    token = request.session.get("auth_token")
    session_token = request.session.get("session_token")
    # print(f"Token: {token}, Session Token: {session_token}")

    if not token or not session_token:
        return redirect("client_login")

    context = {'auth_token': token,
        'session_token': session_token,
        'backend_url': settings.BACKEND_JS_URL,
        'today_date': datetime.now().date()
    }  # Will store both form and result data

    if request.method == "POST":
        stock_code = request.POST.get('stock_code')
        cmp = request.POST.get('cmp')
        atm_strike = request.POST.get('atm_strike')
        days_to_expiry = request.POST.get('days_to_expiry')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        payload = {
            "stock_code": stock_code,
            "cmp": cmp,
            "atm_strike": atm_strike,
            "days_to_expiry": days_to_expiry,
            "start_date": start_date,
            "end_date": end_date,
            "session_token": session_token,
        }

        try:
            response = requests.post(
                settings.BACKEND_BASE_URL + "/api/analysis-view-api/",
                json=payload,
                headers={"Authorization": f"Token {token}"}
            )

            if response.status_code == 200:
                api_data = response.json()
                # print(f"API response data: {api_data}")
                context.update(api_data)  # ✅ Add result data to context
            else:
                print("here")
                context["error"] = response.json().get("error", "Failed to fetch analysis data.")

        except Exception as e:
            context["error"] = str(e)

    return render(request, "analysis.html", context)

@csrf_exempt  # Optional if you use {% csrf_token %} correctly
def square_off_view(request):
    session_token = request.session.get('session_token')
    breeze = get_breeze_for_user(request.user, session_token)
    stock_code = request.POST.get('stock_code')
    expiry_date = request.POST.get('expiry')
    strike_price = request.POST.get('strike')
    right = request.POST.get('right')
    action = request.POST.get('action')
    quantity = request.POST.get("quantity")
    product = request.POST.get("product")
    printing = [stock_code, expiry_date, strike_price,right, action, quantity, product]
    print(printing)
    # Redirect back to open positions
    status, results = square_off(breeze,stock_code, product,expiry_date, right,strike_price, action, quantity)
    # status = False
    # results = "You dont have money bruh"
    if status:
        messages.success(request, "✅ Square off successful.")
    else:
        messages.error(request, f"❌ Square off failed: {results}")

    return redirect('open_positions')

def square_off_bulk_view(request):
    session_token = request.session.get('session_token')
    breeze = get_breeze_for_user(request.user, session_token)
    selected = request.POST.getlist('selected_rows')
    succeeded_orders = []
    failed_orders = []
    for row_data in selected:
        try:
            stock_code, expiry_date, strike_price, right, action, quantity, product = row_data.split('|')
            opposite_action = 'SELL' if action.upper() == 'BUY' else 'BUY'
            # printing.append([stock_code, expiry_date, strike_price, right, action, quantity, product])
            status, results = square_off(breeze, product,expiry_date, right,strike_price, action, quantity)
            contract = f"{stock_code}-{expiry_date}-{strike_price}-{right}"
            if status:
                succeeded_orders.append(contract)

            else:
                failed_orders.append({contract:results})

        except Exception as e:
            print(f"Error squaring off {row_data}: {e}")

    messages.success(request, f"✅ Square off successful for {succeeded_orders}.")
    messages.error(request, f"❌ Square off failed for: {failed_orders}")
    return redirect('open_positions')

@csrf_exempt
def update_ltp(request):
    logger.info(f"Received {request.method} request to fetch LTP")

    if request.method == 'POST':
        session_token = request.session.get('session_token')
        breeze = get_breeze_for_user(request.user, session_token)

        try:
            data = json.loads(request.body)
            stock_code = data.get('stock_code')
            expiry_date = data.get('expiry_date')
            strike_price = data.get('strike_price')
            right = data.get('right')

            logger.info(f"Fetching LTP for stock_code={stock_code}, right={right}, strike_price={strike_price}, expiry_date={expiry_date}")

            option_data = get_option_chain_for_strike(
                breeze, stock_code, right, strike_price,
                exchange_code="NFO", expiry_date=expiry_date
            )

            ltp = option_data[0]["ltp"] if option_data and "ltp" in option_data[0] else None

            if ltp is not None:
                logger.info(f"LTP fetched successfully: {ltp}")
                return JsonResponse({'success': True, 'ltp': ltp})
            else:
                logger.warning(f"LTP not found for stock_code={stock_code}")
                return JsonResponse({'success': False, 'error': 'LTP not found'})

        except Exception as e:
            logger.error(f"Error while fetching LTP: {e}", exc_info=True)
            return JsonResponse({'success': False, 'error': str(e)})

    logger.warning("Invalid request method for get_ltp")
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@csrf_exempt
def square_off_confirm(request):
    if request.method == 'POST':
        post_data = request.POST.dict()
        
        if 'confirm_bulk' in post_data:
            print("in confirm")
            handle_bulk_square_off(request)
            return redirect('open_positions')

        elif 'confirm' in post_data:
            handle_single_square_off(request)
            return redirect('open_positions')

        else:
            # Render confirmation screen
            if "selected_rows" not in request.POST:
                context = {
                    "stock_code": request.POST.get("stock_code"),
                    "expiry": request.POST.get("expiry"),
                    "strike": request.POST.get("strike"),
                    "right": request.POST.get("right"),
                    "action": request.POST.get("action"),
                    "quantity": request.POST.get("quantity"),
                    "product": request.POST.get("product"),
                    "ltp": request.POST.get("ltp"),
                    "avgcost": request.POST.get("avgcost")
                }
                return render(request, "square_off_confirm.html", context)
            else:
                selected = request.POST.getlist("selected_rows")
                bulk_orders = []
                for row in selected:
                    try:
                        stock_code, expiry, strike, right, action, quantity, product, ltp = row.split("|")
                        bulk_orders.append({
                            "stock_code": stock_code,
                            "expiry": expiry,
                            "strike": strike,
                            "right": right,
                            "action": action,
                            "quantity": quantity,
                            "product": product,
                            "ltp": ltp
                        })
                    except Exception as e:
                        messages.error(request, f"⚠️ Invalid order row: {row}")
                return render(request, "square_off_confirm.html", {"bulk_orders": bulk_orders})

    return redirect('open_positions')

def long_running_task(data_rows, user, session_token, right):
    try:
        print("THREAD STARTED")
        print("Data rows:", data_rows)
        print("Length:", len(data_rows))

        breeze = get_breeze_for_user(user, session_token)
        print("Got breeze session")

        batch_size = 20
        total_batches = (len(data_rows) + batch_size - 1) // batch_size
        update_progress(0, total_batches, done=False)

        for i in range(0, len(data_rows), batch_size):
            batch_num = i // batch_size + 1
            print(f"Processing batch {batch_num}")
            update_progress(batch_num, total_batches, done=False)

            batch = data_rows[i:i+batch_size]
            for row in batch:
                # print("Row:", row)
                try:
                    stock_code = row["Stock_code"]
                    expiry_date = row["Expiry_date"]
                    # stock_id = row["Stock_id"]
                    right = right

                    stock_info = stock.get_stock_info_by_code(stock_code)
                    stock_id = stock_info["id"]
                    ltp = stockprice.save_stock_price(breeze, stock_code, stock_id, stock_info["stock_name"])
                    option_chain.save_optionchain(breeze, stock_info, expiry_date, ltp, right)
                except Exception as inner_e:
                    print("Error in row:", inner_e)

            if i + batch_size < len(data_rows):
                print("Sleeping 60s before next batch...")
                import time
                time.sleep(60)

        print("✅ Finished all batches.")
        update_progress(total_batches, total_batches, done=True)

    except Exception as e:
        update_progress(0, 0, done=True)
        print("❌ Thread crashed:", str(e))



# def run_batch_view(request, right):
#     print("here")
#     if request.method == 'POST':
#         try:
#             excel_path = os.path.join(settings.BASE_DIR, 'static', 'Book32.csv')
#             df = pd.read_csv(excel_path)
#             print(right)
#             # print(df)
#             df['user_id'] = request.user.id
#             df['session_token'] = request.session.get('session_token')
#             df["Expiry_date"] = pd.to_datetime(df["Expiry_date"], errors="coerce")

# # Reformat into '%B %d, %Y' → e.g. 'June 26, 2025'
#             df["Expiry_date"] = df["Expiry_date"].dt.strftime('%B %d, %Y')

#             data_rows = df.to_dict(orient='records')
#             thread = threading.Thread(target=long_running_task, args=(data_rows, request.user, request.session.get('session_token'), right))
#             thread.start()

#             return JsonResponse({'status': 'started', 'message': 'Task is running in the background.'})

#         except Exception as e:
#             return JsonResponse({'status': 'error', 'message': str(e)})

#     return JsonResponse({'status': 'error', 'message': 'Invalid method'})

# def batch_status(request):
#     return JsonResponse(get_progress())

@login_required
def export_option_chain_excel(request):
    # Assuming you are fetching this data from your DB
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_full_data()")
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    # Convert to DataFrame
    df = pd.DataFrame(rows)

    # Add yield column (basic formula)
    df["yield"] = df.apply(
        lambda row: round((row["ltp"] * row["lot_size"]) / row["margin"] * 100, 2)
        if row["margin"] else 0,
        axis=1
    )

    # Filter out rows where yield is 0
    df = df[df["yield"] > 0]


    # Clean and prepare Excel response
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='OptionChain', engine_kwargs={"options": {"default_format": {}}})

    output.seek(0)
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=option_chain.xlsx'
    return response

# @login_required(login_url='/client_login')
# def option_chain_view(request):
#     breeze = get_breeze_for_user(request.user)
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT get_option_chain_data();")
#         option_data_grouped = cursor.fetchone()[0]

#     # option_data_grouped = json.loads(result)
#     for item in option_data_grouped:
#         stock = item.get('stock_code')
#         print(stock)
#         item['cmp'] = get_ltp(breeze, stock)

#     return render(request, 'option_chain.html', {
#         'option_data_grouped': option_data_grouped
#     })
