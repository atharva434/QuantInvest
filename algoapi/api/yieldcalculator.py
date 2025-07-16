import pandas as pd
from breeze_connect import BreezeConnect
import json
from tqdm import tqdm
import numpy as np
from .models import UserAccounts
from django.shortcuts import render,redirect
import datetime
import logging
import requests
from django.conf import settings
from django.contrib import messages

logger = logging.getLogger(__name__)

def get_breeze_for_user(user, session_token):
    try:
        client = user.clients.first()
        breeze = BreezeConnect(api_key=client.app_key)
        breeze.generate_session(api_secret=client.secret_key, session_token=session_token)
        logger.info(f"Session generated for user: {user}")
        return breeze
    except UserAccounts.DoesNotExist:
        return redirect("client_login")
        raise Exception("Client details not found")

def get_ltp(breeze ,stock_code):
    try:
        quotes = breeze.get_quotes(
            stock_code=stock_code,
            exchange_code="NSE",
            product_type="cash",
            right="others"
        )
        return quotes["Success"][0]

    except Exception as e:
        logger.error(f"Error fetching quotes for {stock_code}: {e}")
        return 0

def get_option_chain(breeze, stock_code,right, exchange_code="NFO",  expiry_date=None):
    response = breeze.get_option_chain_quotes(
        stock_code=stock_code,
        exchange_code=exchange_code,  # Use "NFO" for NSE F&O
        expiry_date=expiry_date,
        product_type="options",
        right = right,      # Example: "2024-04-25" (optional)
    )
    logger.info(f"Option chain fetched for {stock_code} ({right}): {response}")
    return response["Success"]

def get_option_chain_for_strike(breeze, stock_code,right,strike_price, exchange_code="NFO",  expiry_date=None):
    response = breeze.get_option_chain_quotes(
        stock_code=stock_code,
        strike_price = strike_price,
        exchange_code=exchange_code,  # Use "NFO" for NSE F&O
        expiry_date=expiry_date,
        product_type="options",
        right = right,      # Example: "2024-04-25" (optional)
    )
    return response["Success"]

def get_margin(breeze, stockcode,strikeprice,ltp, quantity, expiry_date, right):
    '''
    Should return the margin
    '''

    margin_json = breeze.margin_calculator([{
            "strike_price": strikeprice,
            "quantity": quantity,
            "price":ltp,
            "right": right,
            "product": "options",
            "action": "sell",
            "expiry_date": expiry_date,
            "stock_code": stockcode,

        },
    ], exchange_code="NFO")
    try:
        return float(margin_json["Success"]["span_margin_required"])+float(margin_json["Success"]["non_span_margin_required"])
    except:
        return 0.0
    

def buy_sell(breeze, stock_code, exchange_code, action, order_type, stoploss, quantity, order_price,
             expiry_date, right, strike_price, lot_size, validity="day", product="options", split_orders=False, max_qty_limit=1800):
    """
    Place buy/sell orders, either as a single order or split into multiple orders.
    Returns a list of result dicts, each with details of the attempt.
    """
    logger.info(f"Placing {action} order for {stock_code}, split_orders={split_orders}")
    results = []

    def place_order_block(qty):
        try:
            status = breeze.place_order(
                stock_code=stock_code,
                exchange_code=exchange_code,
                product=product,
                action=action,
                order_type=order_type,
                stoploss=stoploss,
                quantity=qty,
                price=order_price,
                validity=validity,
                validity_date="2025-04-24",
                disclosed_quantity="0",
                expiry_date=expiry_date,
                right=right,
                strike_price=strike_price
            )
            logger.info(f"Order response for {qty} units of {stock_code}: {status}")
            success_data = status.get("Success")
            
            # If Success is present and order_id exists
            if success_data and "order_id" in success_data:
                return {
                    "status": "success",
                    "order_id": success_data["order_id"],
                    "quantity": qty,
                    "error": None
                }
            
            # If the status is 500, mark the order as failed
            if status.get("Status") == 500:
                return {
                    "status": "failed",
                    "order_id": None,
                    "quantity": qty,
                    "error": f"{status.get('Error', 'Unknown error')}"
                }

            # General failure if no Success and error present
            return {
                "status": "failed",
                "order_id": None,
                "quantity": qty,
                "error": status.get("Error", "Unknown error")
            }
        except Exception as e:
            logger.error(f"Order failed for {qty} units of {stock_code}: {e}")
            return {
                "status": "failed",
                "order_id": None,
                "quantity": qty,
                "error": str(e)
            }

    if not split_orders:
        results.append(place_order_block(quantity))
        return results

    if quantity % lot_size != 0:
        raise ValueError("Total quantity must be a multiple of lot size")

    max_lots_per_order = max_qty_limit // lot_size
    if max_lots_per_order == 0:
        raise ValueError("Lot size exceeds max quantity limit")

    total_lots = quantity // lot_size

    while total_lots > 0:
        lots_this_order = min(total_lots, max_lots_per_order)
        qty_this_order = lots_this_order * lot_size
        result = place_order_block(qty_this_order)
        results.append(result)
        if result["status"] == "failed":
            break
        total_lots -= lots_this_order

    return results


def handle_single_square_off(request):

    try:
        payload = {
            "stock_code": request.POST.get('stock_code'),
            "expiry": request.POST.get('expiry'),
            "strike": request.POST.get('strike'),
            "right": request.POST.get('right'),
            "action": request.POST.get('action'),
            "quantity": request.POST.get('quantity'),
            "product": request.POST.get('product').lower(),
            "order_price": request.POST.get('order_price')
        }
        token = request.session.get("auth_token")
        session_token = request.session.get("session_token")

        # Include session token if needed for auth
        response = requests.post(
            settings.BACKEND_BASE_URL + "/api/square_off/",
            headers={"Authorization": f"Token {token}"},
            params={"session_token": session_token},
            data=payload
        )
        data = response.json()

        if response.status_code == 200 and data.get("status"):
            messages.success(request, f"✅ {data.get('message', 'Square off successful.')}")
        else:
            messages.error(request, f"❌ {data.get('message', 'Square off failed.')}")
    except Exception as e:
        messages.error(request, f"⚠️ Exception: {str(e)}")

def handle_bulk_square_off(request):
    total = int(request.POST.get("total_bulk_orders", 0))
    success_count = 0
    fail_count = 0

    for i in range(1, total + 1):
        try:
            payload = {
                "stock_code": request.POST.get(f"stock_code_{i}"),
                "expiry": request.POST.get(f"expiry_{i}"),
                "strike": request.POST.get(f"strike_{i}"),
                "right": request.POST.get(f"right_{i}"),
                "action": request.POST.get(f"action_{i}"),
                "quantity": request.POST.get(f"quantity_{i}"),
                "product": request.POST.get(f"product_{i}").lower(),
                "order_price": request.POST.get(f"order_price_{i}")
            }

            headers = {
                'Authorization': f'Token {request.session.get("api_token")}',
            }

            url = settings.BACKEND_BASE_URL + "/api/square_off/"
            response = requests.post(url, json=payload, headers=headers)
            data = response.json()

            if response.status_code == 200 and data.get("status"):
                success_count += 1
            else:
                fail_count += 1
                messages.error(request, f"❌ {payload['stock_code']}: {data.get('message', 'Failed')}")
        except Exception as e:
            fail_count += 1
            messages.error(request, f"⚠️ Exception: {str(e)}")

    if success_count:
        messages.success(request, f"✅ {success_count} orders squared off.")

def square_off(breeze, stock_code, product, expiry_date, right, strike_price, price, action, quantity, max_qty_limit=0):
    import datetime
    validity_date = datetime.datetime.now().strftime('%Y-%m-%d')
    results = []
    quantity = int(quantity)

    def square_off_block(qty):
        try:
            status = breeze.square_off(
                exchange_code="NFO",
                product=product,
                stock_code=stock_code,
                expiry_date=expiry_date,
                right=right,
                strike_price=strike_price,
                action=action,
                quantity=qty,
                price=price,
                order_type="limit",
                validity="day",
                validity_date=validity_date,
                trade_password="",
                disclosed_quantity="0"
            )
            logger.info(f"Square-off response: {status}")
            success_data = status.get("Success")
            if success_data:
                return {"status": "success", "data": success_data, "quantity": qty}
            else:
                return {"status": "failed", "data": status, "quantity": qty}
        except Exception as e:
            return {"status": "failed", "data": str(e), "quantity": qty}

    # ✅ Slicing logic without using lot_size
    if max_qty_limit > 0:
        
        remaining = quantity
        while remaining > 0:
            qty_this_order = min(remaining, max_qty_limit)
            result = square_off_block(qty_this_order)
            results.append(result)
            if result["status"] == "failed":
                break
            remaining -= qty_this_order

        all_success = all(r["status"] == "success" for r in results)
        return (all_success, results)
    else:
       logger.info(f"Initiating square-off for {stock_code}, quantity={quantity}")
       result = square_off_block(quantity) 
       results.append(result)
       return ([True], results)










        


        

