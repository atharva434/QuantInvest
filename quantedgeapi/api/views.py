from django.shortcuts import render

# Create your views here.
from matplotlib.dates import relativedelta
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User, Group
from .serializers import UserInfoSerializer, ClientRegistrationSerializer
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from api import open_positions, yieldcalculator
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
import numpy as np
import logging
import json
from .services import option_chain_service
from api import stock, stockprice, option_chain, utils, transactions, stockexpiry
logger = logging.getLogger(__name__)
import os
from django.conf import settings
import threading
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
from django.db import transaction
import pandas as pd
import re
from api import analysis

@api_view(['POST'])
@permission_classes([AllowAny])
def register_client(request):
    data = request.data

    user_data = {
        'username': data.get('username'),
        'password': data.get('password')
    }

    client_data = {
        'acc_name': data.get('acc_name'),
        'acc_provider': data.get('acc_provider'),
        'app_key': data.get('app_key'),
        'secret_key': data.get('secret_key')
    }

    user_serializer = UserInfoSerializer(data=user_data)
    client_serializer = ClientRegistrationSerializer(data=client_data)

    if user_serializer.is_valid() and client_serializer.is_valid():
        user = user_serializer.save()
        user.set_password(user_data['password'])
        user.save()

        client_serializer.save(user=user)

        group, _ = Group.objects.get_or_create(name='UserAccounts')
        group.user_set.add(user)

        return Response({"message": "Registered successfully"}, status=status.HTTP_201_CREATED)

    return Response({
        "user_errors": user_serializer.errors,
        "client_errors": client_serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def login_user(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(username=username, password=password)
    if user:
        token, _ = Token.objects.get_or_create(user=user)

        # Save session_token to client model if needed
        client = user.clients.first()
        if client:
            # If you're saving a session_token, handle it here
            client.save()

        return Response({
            "token": token.key,
            "username": user.username
        }, status=status.HTTP_200_OK)  # ✅ Success status

    return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)



@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_open_positions(request):
    session_token = request.query_params.get("session_token")  # from frontend

    breeze = yieldcalculator.get_breeze_for_user(request.user, session_token)
    positions = open_positions.get_open_positions(breeze)

    if not positions:
        return Response({"grouped_data": []})

    df = pd.DataFrame(positions)
    df = df[df["exchange_code"] == "NFO"]
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df = df[df["quantity"] > 0]
    df["ltp"] = pd.to_numeric(df["ltp"], errors="coerce")
    df["average_price"] = pd.to_numeric(df["average_price"], errors="coerce")
    df["pnl"] = pd.to_numeric(df.get("pnl", None), errors="coerce")

    if df["pnl"].isnull().all():
        df["PL"] = df.apply(
            lambda row: (row["average_price"] - row["ltp"]) * row["quantity"]
            if row["action"].strip().lower() == "sell"
            else (row["ltp"] - row["average_price"]) * row["quantity"],
            axis=1
        )
        df["PL"] = df["PL"].round(2)
    else:
        df["PL"] = df["pnl"]

    df.rename(columns={
        "stock_code": "StockCode",
        "strike_price": "Strike",
        "right": "Right",
        "action": "Action",
        "quantity": "Qty",
        "average_price": "AvgCost",
        "ltp": "LTP",
        "expiry_date": "Expiry"
    }, inplace=True)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.fillna(0, inplace=True)
    grouped_data = []
    for stock_code, group in df.groupby("StockCode"):
        group_data = group.copy()
        total_row = {
            "StockCode": stock_code,
            "Contract": "Total",
            "Qty": group_data["Qty"].sum(),
            "AvgCost": "",
            "LTP": "",
            "PL": group_data["PL"].sum()
        }
        grouped_data.append({
            "stock_code": stock_code,
            "rows": group_data.to_dict(orient="records"),
            "total": total_row
        })
    # print(grouped_data)
    return Response({"grouped_data": grouped_data})


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def trade_pnl_summary_api(request):
    session_token = request.query_params.get("session_token")
    breeze = yieldcalculator.get_breeze_for_user(request.user, session_token)

    try:
        with open("api/index_scripts.json") as f:
            index_scripts = json.load(f)
        indexes = index_scripts["Index"]
    except Exception as e:
        logger.error(f"Error loading index_scripts.json: {e}", exc_info=True)
        indexes = []

    try:
        positions = open_positions.get_open_positions(breeze)
        df = pd.DataFrame(positions)
        df = df[df["exchange_code"] == "NFO"]
    except Exception as e:
        logger.error(f"Error fetching open positions: {e}", exc_info=True)
        df = pd.DataFrame()

    try:
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
        df["ltp"] = pd.to_numeric(df["ltp"], errors="coerce")
        df["average_price"] = pd.to_numeric(df["average_price"], errors="coerce")
        df["pnl"] = pd.to_numeric(df.get("pnl", None), errors="coerce")

        df["realizedpl"] = df.apply(
            lambda row: row["average_price"] * row["quantity"] if row["action"].strip().lower() == "sell"
            else row["average_price"] * row["quantity"] * (-1),
            axis=1
        ).round(2)

        if df["pnl"].isnull().all():
            df["PL"] = df.apply(
                lambda row: row["ltp"] * row["quantity"] * (-1)
                if row["action"].strip().lower() == "sell"
                else row["ltp"] * row["quantity"],
                axis=1
            ).round(2)
        else:
            df["PL"] = df["pnl"]
            df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce")

        df["strike_price"] = pd.to_numeric(df["strike_price"], errors="coerce")
        df["is_index"] = df["stock_code"].isin(indexes).astype(int)
        df["right_order"] = df["right"].str.lower().map({"call": 0, "put": 1})
        df["action_order"] = df["action"].str.lower().map({"buy": 0, "sell": 1})
        df.sort_values(
            by=["is_index", "stock_code", "expiry_date", "right_order", "strike_price", "action_order"],
            ascending=[False, True, True, True, True, True],
            inplace=True
        )
    except Exception as e:
        logger.error(f"Error processing positions: {e}", exc_info=True)
        df = pd.DataFrame()

    # Get holdings
    try:
        holdings = open_positions.get_portfolio_holdings(breeze)
        if holdings:
            df_holdings = pd.DataFrame(holdings)
            df_holdings["stock_code"] = df_holdings["stock_code"].str.strip()
            df_holdings["quantity"] = pd.to_numeric(df_holdings["quantity"], errors="coerce").fillna(0)
            df_holdings["average_price"] = pd.to_numeric(df_holdings["average_price"], errors="coerce").fillna(0)
            df_holdings["ltp"] = pd.to_numeric(df_holdings["current_market_price"], errors="coerce").fillna(0)
            df_holdings["realizedpl"] = pd.to_numeric(df_holdings["realized_profit"], errors="coerce").fillna(0)
            df_holdings["PL"] = pd.to_numeric(df_holdings["unrealized_profit"], errors="coerce").fillna(0)

            df_holdings["action"] = df_holdings.get("action", "Buy")
            df_holdings["right"] = df_holdings.get("right", "")
            df_holdings["expiry_date"] = pd.to_datetime(df_holdings.get("expiry_date", None), errors="coerce")
            df_holdings["strike_price"] = pd.to_numeric(df_holdings.get("strike_price", None), errors="coerce")
            df_holdings["source"] = "Holding"

            df_holdings = df_holdings[[
                "stock_code", "quantity", "average_price", "ltp", "realizedpl", "PL",
                "action", "right", "expiry_date", "strike_price", "source", "product_type"
            ]]
        else:
            df_holdings = pd.DataFrame()
    except Exception as e:
        logger.error(f"Error processing holdings: {e}", exc_info=True)
        df_holdings = pd.DataFrame()

    # Combine and finalize
    try:
        df_combined = pd.concat([df, df_holdings], ignore_index=True)
        df_combined.replace([np.inf, -np.inf], np.nan, inplace=True)
        df_combined.fillna(0, inplace=True)

        df_dict = df_combined.to_dict(orient='records')
        total_realized = sum(row['realizedpl'] for row in df_dict)
        total_unrealized = sum(row['PL'] for row in df_dict)
        total_pnl = total_realized + total_unrealized
    except Exception as e:
        logger.error(f"Final aggregation failed: {e}", exc_info=True)
        df_dict, total_realized, total_unrealized, total_pnl = [], 0, 0, 0

    return Response({
        'df': df_dict,
        'total_realized': round(total_realized, 2),
        'total_unrealized': round(total_unrealized, 2),
        'total_pnl': round(total_pnl, 2),
    })


@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_full_table_data(request):
    session_token = request.GET.get("session_token")
    option_data_grouped, ltp_missing_codes = option_chain_service.get_grouped_option_chain()

    return Response({
        "option_data_grouped": option_data_grouped,
        "ltp_missing": list(ltp_missing_codes)
    })


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def process_selected_stocks_backend(request):
    try:
        t0 = datetime.now()
        logger.info(f"[{t0}] Started processing")

        user = request.user
        session_token = request.query_params.get("session_token")

        if not session_token:
            return Response({'status': 'error', 'message': 'Missing session token'}, status=400)

        t1 = datetime.now()
        logger.info(f"[{t1}] Fetched user and session_token — Elapsed: {(t1 - t0).total_seconds()}s")

        breeze = yieldcalculator.get_breeze_for_user(user, session_token)

        t2 = datetime.now()
        logger.info(f"[{t2}] Breeze object fetched — Elapsed: {(t2 - t1).total_seconds()}s")

        total = int(request.data.get("total_items", 0))

        for i in range(1, total + 1):
            if request.data.get(f'selected_{i}'):
                t_stock_start = datetime.now()

                stock_code = request.data.get(f'stock_code_{i}')
                expiry_date = request.data.get(f'expiry_date_{i}')
                right = request.data.get(f'right_{i}')

                stock_info = stock.get_stock_info_by_code(stock_code)
                stock_id = stock_info["id"]

                ltp = stockprice.save_stock_price(
                    breeze, stock_code, stock_id, stock_info["stock_name"], stock_info["exchange_code"]
                )

                t3 = datetime.now()
                logger.info(f"[{t3}] LTP saved for {stock_code} — Elapsed: {(t3 - t_stock_start).total_seconds()}s")

                option_chain.save_optionchain(
                    breeze=breeze,
                    stock_info=stock_info,
                    expiry_date=expiry_date,
                    base_ltp=ltp,
                    right=right
                )

                t4 = datetime.now()
                logger.info(f"[{t4}] Option chain saved for {stock_code} — Elapsed: {(t4 - t3).total_seconds()}s, Total: {(t4 - t_stock_start).total_seconds()}s")

        t_final = datetime.now()
        logger.info(f"[{t_final}] Completed all processing — Total Elapsed: {(t_final - t0).total_seconds()}s")

        return Response({'status': 'success'})

    except Exception as e:
        logger.error(f"Backend error processing selected stocks: {str(e)}", exc_info=True)
        return Response({'status': 'error', 'message': 'An error occurred in backend'}, status=500)
    

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def calculate_yield_backend(request):

    try:
        user = request.user
        session_token = request.query_params.get("session_token")

        if not session_token:
            return Response({'status': 'error', 'message': 'Missing session token'}, status=400)

        breeze = yieldcalculator.get_breeze_for_user(user, session_token)

        total = int(request.data.get('total_items', 0))
        results = []
        print(total)

        for i in range(1, total + 1):
            if request.data.get(f'selected_{i}'):
                try:
                    stock_code = request.data.get(f'stock_code_{i}')
                    expiry_date = request.data.get(f'expiry_date_{i}')
                    right = request.data.get(f'right_{i}')
                    strike_price = float(request.data.get(f'strike_price_{i}', 0))
                    lot_size = float(request.data.get(f'lot_size_{i}', 0))
                    lots = int(request.data.get(f'lots_{i}', 1))

                    option_chain = yieldcalculator.get_option_chain_for_strike(
                        breeze=breeze,
                        stock_code=stock_code,
                        right=right,
                        strike_price=strike_price,
                        expiry_date=expiry_date
                    )
                    ltp = option_chain[0]["ltp"]
                    margin = yieldcalculator.get_margin(
                        breeze=breeze,
                        stockcode=stock_code,
                        strikeprice=strike_price,
                        ltp=ltp,
                        quantity=lot_size * lots,
                        expiry_date=expiry_date,
                        right=right,
                    )

                    try:
                        current_price = yieldcalculator.get_ltp(breeze=breeze, stock_code=stock_code)["ltp"]
                    except Exception as e:
                        current_price = 0

                    yield_value = (ltp * lot_size * lots) / margin * 100 if margin else 0

                    results.append({
                        "stock_code": stock_code,
                        "right": right,
                        "yield_value": yield_value,
                        "ltp": ltp,
                        "margin": margin,
                        "cmp": current_price
                    })

                except Exception as e:
                    logger.error(f"Error calculating yield for stock {i}: {e}", exc_info=True)

        return Response({"status": "success", "data": results})

    except Exception as e:
        logger.error(f"Backend error in calculate_yield_backend: {e}", exc_info=True)
        return Response({'status': 'error', 'message': 'Unexpected server error'}, status=500)
    

def long_running_task(data_rows, user, session_token, right):
    try:
        print("THREAD STARTED")
        print("Data rows:", data_rows)
        print("Length:", len(data_rows))

        breeze = yieldcalculator.get_breeze_for_user(user, session_token)
        print("Got breeze session")

        batch_size = 20
        total_batches = (len(data_rows) + batch_size - 1) // batch_size
        utils.update_progress(0, total_batches, done=False)

        for i in range(0, len(data_rows), batch_size):
            batch_num = i // batch_size + 1
            print(f"Processing batch {batch_num}")
            utils.update_progress(batch_num, total_batches, done=False)

            batch = data_rows[i:i+batch_size]
            for row in batch:
                # print("Row:", row)
                try:
                    stock_code = row["Stock_code"]
                    print(stock_code)
                    expiry_date = row["Expiry_date"]
                    # stock_id = row["Stock_id"]
                    right = right

                    stock_info = stock.get_stock_info_by_code(stock_code)
                    stock_id = stock_info["id"]
                    ltp = stockprice.save_stock_price(breeze, stock_code, stock_id, stock_info["stock_name"], exchange_code=stock_info["exchange_code"])
                    option_chain.save_optionchain(breeze, stock_info, expiry_date, ltp, right,exchange_code=stock_info["fno_exchange_code"])
                except Exception as inner_e:
                    print(stock_code)
                    print("Error in row:", inner_e)

            if i + batch_size < len(data_rows):
                print("Sleeping 60s before next batch...")
                import time
                time.sleep(60)

        print("✅ Finished all batches.")
        utils.update_progress(total_batches, total_batches, done=True)

    except Exception as e:
        utils.update_progress(0, 0, done=True)
        print("❌ Thread crashed:", str(e))


@api_view(['POST', 'OPTIONS'])
@authentication_classes([TokenAuthentication])
def run_batch_view(request, right):
    print("here")
    if request.method == 'POST':
        try:
            df = pd.DataFrame()
            print(request.query_params.get("session_token"))
            batch_date = request.POST.get("batch_date")
            print(batch_date)
            # print(df)
            print(request.user)
            df["Stock_code"] = [stk.stock_code for stk in stock.fetch_all_stocks()]
            df["Expiry_date"] = pd.to_datetime(batch_date, errors="coerce")

# Reformat into '%B %d, %Y' → e.g. 'June 26, 2025'
            df["Expiry_date"] = df["Expiry_date"].dt.strftime('%B %d, %Y')
            df["valid"] = 0
            for i, row in df.iterrows():
                try:
                    if row.Stock_code=="NIFTY":
                        print(row.Expiry_date)
                    expiry_date = row.Expiry_date
                    expiry_date = datetime.strptime(expiry_date, "%B %d, %Y").strftime("%Y-%m-%d")
                    expiry_id = stockexpiry.get_stock_expiry_id(row.Stock_code, expiry_date)
                    if expiry_id:
                        print("here")
                        df.loc[i,"valid"] = 1
                except:
                    continue
            df = df[df["valid"]==1]
            data_rows = df.to_dict(orient='records')
            thread = threading.Thread(target=long_running_task, args=(data_rows, request.user, request.query_params.get("session_token"), right))
            thread.start()

            return Response({'status': 'started', 'message': 'Task is running in the background.'})

        except Exception as e:
            print("here", e)
            return Response({'status': 'error', 'message': str(e)})

    return Response({'status': 'error', 'message': 'Invalid method'})

@api_view(['GET'])
def batch_status(request):
    return Response(utils.get_progress())

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_strikes_by_stock_and_right_api(request):
    stock_code = request.GET.get("stock_code")
    right = request.GET.get("right")

    if not stock_code or not right:
        return Response({"error": "Missing stock_code or right parameter"}, status=400)

    try:
        strikes = option_chain.get_strikes_by_stock_and_right(stock_code, right)
        return Response({"strikes": strikes}, status=200)

    except Exception as e:
        logger.error(f"Error fetching strikes: {e}")
        return Response({"error": "Failed to fetch strikes"}, status=500)
    
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def place_order(request):
    if request.method == 'POST':
        logger.info("Received POST request for placing orders")

        session_token = request.query_params.get("session_token")
        breeze = yieldcalculator.get_breeze_for_user(request.user, session_token)
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
            print(stock_code)
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
                    exchange_code = "NFO"
                    action = request.POST.get(f"action_{i}")
                    order_type = request.POST.get(f"order_type_{i}")
                    stop_loss = request.POST.get(f"stoploss_{i}")
                    stop_loss = int(stop_loss) if stop_loss else 0

                    quantity = int(request.POST.get(f"quantity_{i}"))
                    order_price = request.POST.get(f"order_price_{i}")
                    order_price = float(order_price) if order_price else None

                    expiry_date = request.POST.get(f"expiry_date_{i}")
                    try:
                        parsed_date = datetime.strptime(expiry_date, '%B %d, %Y')
                        expiry_date = parsed_date.strftime('%Y-%m-%d')

                    except:
                        expiry_date = expiry_date

                    right = request.POST.get(f"right_{i}")
                    strike_price = request.POST.get(f"strike_price_{i}")
                    strike_price = float(strike_price) if strike_price else 0.0

                    lot_size = int(request.POST.get(f"lot_size_{i}"))

                    with open("api/order_limit.json") as f:
                        order_limit = json.load(f)

                    if stock_code in order_limit:
                        logger.info(f"Stock {stock_code} has an order limit. Applying max_qty_limit: {order_limit[stock_code]}")
                        order_ids = yieldcalculator.buy_sell(
                            breeze, stock_code, exchange_code, action, order_type,
                            stop_loss, quantity, order_price,
                            expiry_date, right, strike_price, lot_size,
                            split_orders=True,
                            max_qty_limit=order_limit[stock_code]
                        )
                    else:
                        logger.info(f"Stock {stock_code} has no order limit. Proceeding without quantity split.")
                        order_ids = yieldcalculator.buy_sell(
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
        return Response({'success': True, 'results': results})

    return Response({'success': False, 'message': 'Invalid request method'})



@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def square_off_api(request):
    try:
        session_token = request.query_params.get("session_token")
        breeze = yieldcalculator.get_breeze_for_user(request.user, session_token)
        data = request.data
        stock_code = data.get('stock_code')
        expiry = datetime.strptime(data.get('expiry'), '%d-%b-%Y').strftime('%Y-%m-%d')
        action = data.get('action')
        reverse_action = 'sell' if action.upper() == 'BUY' else 'buy'

        with open("api/order_limit.json") as f:
            order_limit = json.load(f)
        max_qty_limit = order_limit.get(stock_code, 0)

        status, result = yieldcalculator.square_off(
            breeze,
            stock_code,
            data.get('product').lower(),
            expiry,
            data.get('right'),
            data.get('strike'),
            data.get('order_price'),
            reverse_action,
            data.get('quantity'),
            max_qty_limit
        )

        return Response({'status': True , 'message': result})
    except Exception as e:
        return Response({'status': False, 'message': str(e)})
    


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_ltp(request):
    logger.info(f"Received {request.method} request to fetch LTP")

    if request.method == 'POST':
        session_token = request.query_params.get("session_token")
        breeze = yieldcalculator.get_breeze_for_user(request.user, session_token)

        try:
            data = json.loads(request.body)
            stock_code = data.get('stock_code')
            expiry_date = data.get('expiry_date')
            strike_price = data.get('strike_price')
            right = data.get('right')

            logger.info(f"Fetching LTP for stock_code={stock_code}, right={right}, strike_price={strike_price}, expiry_date={expiry_date}")

            option_data = yieldcalculator.get_option_chain_for_strike(
                breeze, stock_code, right, strike_price,
                exchange_code="NFO", expiry_date=expiry_date
            )

            ltp = option_data[0]["ltp"] if option_data and "ltp" in option_data[0] else None

            if ltp is not None:
                logger.info(f"LTP fetched successfully: {ltp}")
                return Response({'success': True, 'ltp': ltp})
            else:
                logger.warning(f"LTP not found for stock_code={stock_code}")
                return Response({'success': False, 'error': 'LTP not found'})

        except Exception as e:
            logger.error(f"Error while fetching LTP: {e}", exc_info=True)
            return Response({'success': False, 'error': str(e)})

    logger.warning("Invalid request method for get_ltp")
    return Response({'success': False, 'error': 'Invalid request method'})

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_expiry_dates_api(request):
    stock_code = request.query_params.get("stock_code")
    
    logger.info("🔍 [get_expiry_dates_api] Called by user: %s", request.user)
    logger.info("📦 Received stock_code: %s", stock_code)

    if not stock_code:
        logger.warning("❌ Missing stock_code in request")
        return Response({'error': 'Missing stock_code'}, status=400)

    try:
        dates = analysis.get_expiry_dates_for_stock(stock_code)
        logger.info("✅ Found %d expiry dates for stock_code %s", len(dates), stock_code)
        return Response({'expiry_dates': dates})
    except Exception as e:
        logger.exception("💥 Error in get_expiry_dates_api for stock_code %s", stock_code)
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_stock_info_api(request):
    stock_code = request.query_params.get("stock_code")
    logger.debug(f"[DEBUG] Received request for stock_code: {stock_code}")

    if not stock_code:
        logger.error("[ERROR] Missing stock_code in request")
        return Response({'error': 'Missing stock_code'}, status=400)

    try:
        logger.debug(f"[DEBUG] Fetching min/max info for: {stock_code}")
        info = analysis.get_stock_min_max_info(stock_code)

        if not info:
            logger.warning(f"[WARN] No data found for stock_code: {stock_code}")
            return Response({'error': 'No data found'}, status=404)

        logger.debug(f"[DEBUG] Returning stock info for {stock_code}: {info}")
        return Response(info)
    except Exception as e:
        logger.exception(f"[EXCEPTION] Error in get_stock_info_api for {stock_code}")
        return Response({'error': str(e)}, status=500)

    
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_analysis_inputs_api(request):
    """
    DRF view for JS to fetch CMP, ATM strike, nearest strike, min/max dates etc.
    """
    stock_code = request.query_params.get("stock_code")
    expiry_date = request.query_params.get("expiry_date")
    session_token = request.query_params.get("session_token")

    logger.debug(f"[DEBUG] API called with stock_code={stock_code}, expiry_date={expiry_date}, session_token={session_token}")

    if not stock_code or not expiry_date or not session_token:
        logger.error("[ERROR] Missing one or more required query parameters.")
        return Response({'error': 'Missing required parameters'}, status=400)

    try:
        logger.debug(f"[DEBUG] Getting Breeze session for user: {request.user}")
        breeze = yieldcalculator.get_breeze_for_user(request.user, session_token)

        logger.debug(f"[DEBUG] Calling get_analysis_inputs for stock={stock_code}, expiry={expiry_date}")
        data = analysis.get_analysis_inputs(stock_code, expiry_date, breeze)

        logger.debug(f"[DEBUG] Data returned: {data}")
        return Response(data)
    except Exception as e:
        logger.exception("[EXCEPTION] Error in get_analysis_inputs_api")
        return Response({'error': str(e)}, status=500)

    

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_stock_codes_api(request):
    try:
        logger.debug(f"[DEBUG] get_stock_codes_api called by user: {request.user}")
        
        stock_codes = analysis.fetch_valid_stock_codes()
        
        logger.debug(f"[DEBUG] Retrieved {len(stock_codes)} stock codes.")
        return Response({'stock_codes': stock_codes})
    except Exception as e:
        logger.exception("[EXCEPTION] Error in get_stock_codes_api")
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def analysis_view_api(request):
    try:
        logger.debug("[DEBUG] analysis_view_api called by: %s", request.user)

        stock_code = request.data.get('stock_code', '').upper()
        cmp = float(request.data.get('cmp', 0))
        atm_strike = float(request.data.get('atm_strike', 0))
        days_to_expiry = int(request.data.get('days_to_expiry', 0))
        start_date = datetime.strptime(request.data.get('start_date'), "%Y-%m-%d").date()
        end_date = datetime.strptime(request.data.get('end_date'), "%Y-%m-%d").date()

        logger.debug(
            "[DEBUG] Inputs: stock_code=%s, cmp=%s, atm_strike=%s, days_to_expiry=%s, start_date=%s, end_date=%s",
            stock_code, cmp, atm_strike, days_to_expiry, start_date, end_date
        )

        rows = analysis.fetch_daily_stock_data(stock_code, start_date, end_date)
        if not rows:
            logger.debug("[DEBUG] No data found for given stock and date range.")
            return Response({'error': 'No data found for selected stock and date range'}, status=404)

        logger.debug("[DEBUG] Fetched %d rows of stock data.", len(rows))

        df = pd.DataFrame(rows, columns=['Date', 'Open', 'Close', 'Expiry Date', 'High', 'Low'])
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        df['Expiry Date'] = pd.to_datetime(df['Expiry Date'], errors='coerce').dt.date

        start_date = pd.Timestamp(start_date)
        end_date = pd.Timestamp(end_date)

        logger.debug("[DEBUG] Running pseudo vs expiry move calculation...")
        days_moves_dict = analysis.get_pseudo_vs_expiry_moves(df, start_date, end_date, days_to_expiry)
        days_moves = list(days_moves_dict.values())

        for move in days_moves:
            if 'percent_move' not in move and 'pct_move' in move:
                move['percent_move'] = move.pop('pct_move')

        logger.debug("[DEBUG] Processing %d days_to_expiry moves...", len(days_moves))
        context = {}
        context.update(analysis.process_days_moves(days_moves, cmp, stock_code, "days_to_expiry"))

        logger.debug("[DEBUG] Running monthly expiry move calculation...")
        monthly_moves = analysis.calculate_monthly_moves_from_expiry(df, start_date, end_date)

        for move in monthly_moves:
            if 'percent_move' not in move and 'pct_move' in move:
                move['percent_move'] = move.pop('pct_move')
            expiry_date = move.get("expiry_date") or move.get("Expiry Date")
            if expiry_date:
                move['base_close'] = analysis.get_expiry_close_from_rows(df, expiry_date)

        logger.debug("[DEBUG] Processing %d monthly_expiry moves...", len(monthly_moves))
        context.update(analysis.process_monthly_moves(monthly_moves, stock_code, df, name_prefix="monthly_expiry"))

        delta = relativedelta(end_date, start_date)
        months = delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)

        context.update({
            'stock_code': stock_code,
            'cmp': cmp,
            'atm_strike': atm_strike,
            'days_to_expiry': days_to_expiry,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'movement_range_label': f"Movement for {months} month{'s' if months != 1 else ''}"
        })

        logger.debug("[DEBUG] Final context ready to return.")
        return Response(context)

    except Exception as e:
        logger.exception("[EXCEPTION] Error in analysis_view_api")
        return Response({'error': str(e)}, status=500)
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_option_chain(request):

        data = request.data
        total_items = int(data.get('total_items', 0))
        updated_orders = []

        for i in range(total_items):
            stock_code = data.get(f'stock_code_{i}')
            expiry_date = data.get(f'expiry_date_{i}')
            right = data.get(f'right_{i}')

            # Mock logic — replace with actual DB or API call
            # Just slightly tweaking the values here for example
            session_token = request.query_params.get("session_token")
            breeze = yieldcalculator.get_breeze_for_user(request.user, session_token)
            # print(yieldcalculator.get_option_chain(breeze, stock_code,right,  expiry_date=expiry_date))
            option_chain = yieldcalculator.get_option_chain(breeze, stock_code,right,  expiry_date=expiry_date)
            strike_prices = [chain["strike_price"] for chain in option_chain]
            order_prices = [chain["ltp"] for chain in option_chain]
            best_bid_prices = [chain["best_bid_price"] for chain in option_chain]
            best_offer_prices = [chain["best_offer_price"] for chain in option_chain]
    

            updated_order = {
                "strike_prices":strike_prices,
                "order_prices": order_prices,
                "best_bid_prices":best_bid_prices,
                "best_offer_prices":best_offer_prices
            }

            updated_orders.append(updated_order)

        return Response({"updated_orders": updated_orders}, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_valid_expiries_api(request):
    
    logger.info("🔍 [get_expiry_dates_api] Called by user: %s", request.user)

    try:
        dates = analysis.get_valid_expiries()
        # logger.info("✅ Found %d expiry dates %s", len(dates),)
        return Response({'expiry_dates': dates})
    except Exception as e:
        logger.exception("💥 Error in get_expiry_dates_api for stock_code %s")
        return Response({'error': str(e)}, status=500)

    # except Exception as e:
    #     print(e)
    #     return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
