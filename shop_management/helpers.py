import httpx # type: ignore
import asyncio

import json
import uuid

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from time import time
from datetime import timedelta
from django.utils import timezone
from .models import CustomSession
from functools import wraps
from django.http import JsonResponse, HttpResponse
from functools import wraps
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from .models import Customers, Shopkeepers


def authenticate_user(username: str, password: str):
    user = authenticate(username=username, password=password)
    if user and user.is_superuser:
        return user, 'superuser'
    
    try:
        shopkeeper = Shopkeepers.objects.get(username=username, deleted_at__isnull=True)
        if check_password(password, shopkeeper.password):
            return shopkeeper, 'shopkeeper'
    except Shopkeepers.DoesNotExist:
        pass
    
    try:
        customer = Customers.objects.get(username=username, deleted_at__isnull=True)
        if check_password(password, customer.password):
            return customer, 'customer'
    except Customers.DoesNotExist:
        pass
    
    return None, None


def timed_response(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        start = time()
        data = func(request, *args, **kwargs)
        end = time()
        duration = round(end - start, 3)

        if isinstance(data, HttpResponse):
            return data

        if isinstance(data, dict) and 'error' in data:
            return JsonResponse(data, status=data.get('status_code', 400))

        return JsonResponse({
            "api_name": func.__name__,
            "data": data,
            "status": "success",
            "time_taken": f"{duration}s"
        })
    return wrapper


def create_session(user_obj, role, duration_hours=4):
    expires_at = timezone.now() + timedelta(hours=duration_hours)
    session = CustomSession.objects.create(
        session_id=str(uuid.uuid4()),
        customer=user_obj if role == 'customer' else None,
        shopkeeper=user_obj if role == 'shopkeeper' else None,
        user = user_obj if role== 'superuser' else None,
        expires_at=expires_at
    )
    return session

def _authorize_shopkeeper(request):
    shopkeeper = getattr(request, 'shopkeeper', None)
    if shopkeeper and not shopkeeper.deleted_at:
        return shopkeeper
    return None

def _authorize_customer(request):
    customer = getattr(request, 'customer', None)
    if customer and not customer.deleted_at:
        return customer
    return None

def _authorize_superuser(request):
    user = getattr(request, 'user', None)
    if user and user.is_active and user.is_superuser:
        return user
    return None


def pagination_helper(items, page=1, page_size=10):
    total_items = len(items)
    total_pages = total_items // page_size + (1 if total_items % page_size != 0 else 0)
    
    if total_pages == 0:
        total_pages = 1  # at least 1 page

    if page < 1 or page > total_pages:
        return None, total_pages

    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], total_pages


# Helper coroutine to fetch a single URL
async def fetch(client, req, cookies=None):
    method = req.get("method").upper()
    url = req["url"]
    body = req.get("body", None)
    params = req.get("params", None)
    
    if method == "GET":
        res = await client.get(url,params=params, cookies=cookies)
    elif method == "POST":
        if not body and params:
            return "POST requests require a body"
        res = await client.post(url, json=body, cookies=cookies)
    elif method == "PUT":
        if not body and params:
            return "PUT requests require a body"
        res = await client.put(url, json=body, cookies=cookies)
    elif method == "DELETE":
        if not body and params:
            return "DELETE requests require a body"
        res = await client.delete(url, json=body, cookies=cookies)
    else:
        return f"Method {method} not supported"

    try:
        return res.json()
    except:
        return res.text


@csrf_exempt

async def fetch_multiple_requests(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        body = json.loads(request.body)
        requests_list = body.get("requests", [])
    except:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    if not requests_list:
        return JsonResponse({"error": "No requests provided"}, status=400)
    
    cookies = {}
    
    shop_session = request.COOKIES.get("SHOPKEEPER_SESSIONID")
    cust_session = request.COOKIES.get("CUSTOMER_SESSIONID")
    
    if shop_session:
        cookies["SHOPKEEPER_SESSIONID"] = shop_session
    elif cust_session:
        cookies["CUSTOMER_SESSIONID"] = cust_session

    
    async with httpx.AsyncClient() as client:
        
        for req in requests_list:
            if "method" not in req or "url" not in req:
                return JsonResponse({"error": "Each request must have 'method' and 'url'"}, status=400)
        
        tasks = [fetch(client, req, cookies) for req in requests_list ]
        results = await asyncio.gather(*tasks)
    
    return JsonResponse({req["url"]: res for req, res in zip(requests_list, results)})



