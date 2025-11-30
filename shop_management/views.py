import uuid
import json
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Sum, Count
from django.views.decorators.csrf import csrf_exempt
from .models import Customers, Shopkeepers, Products, Orders, Categories,CustomSession
from django.core.cache import cache
from shop_management.helpers import authenticate_user,timed_response, create_session, _authorize_shopkeeper, _authorize_customer,_authorize_superuser, pagination_helper
from django.contrib.auth.hashers import make_password

@csrf_exempt
@timed_response
def login_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
    except:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not username or not password:
        return JsonResponse({'error': 'Username and password required'}, status=400)

    user_obj, role = authenticate_user(username, password)
    if not user_obj:
        return JsonResponse({'error': 'Invalid credentials'}, status=401)

    CustomSession.objects.filter(expires_at__lt=timezone.now()).delete()

    if role == 'superuser':
        active_session = CustomSession.objects.filter(user=user_obj, expires_at__gt=timezone.now()).first()
        cookie_name = 'SUPERUSER_SESSIONID'
    elif role == 'shopkeeper':
        active_session = CustomSession.objects.filter(shopkeeper=user_obj, expires_at__gt=timezone.now()).first()
        cookie_name = 'SHOPKEEPER_SESSIONID'
    else:
        active_session = CustomSession.objects.filter(customer=user_obj, expires_at__gt=timezone.now()).first()
        cookie_name = 'CUSTOMER_SESSIONID'

    if active_session:
        return JsonResponse({
            'message': 'Already logged in',
            'role': role.capitalize(),
        }, status=200)

    if role == 'shopkeeper' and CustomSession.objects.filter(customer__isnull=False, expires_at__gt=timezone.now()).exists():
        return JsonResponse({'error': 'A customer is already logged in.'}, status=403)
    if role == 'customer' and CustomSession.objects.filter(shopkeeper__isnull=False, expires_at__gt=timezone.now()).exists():
        return JsonResponse({'error': 'A shopkeeper is already logged in.'}, status=403)

    session = create_session(user_obj, role)
    response = JsonResponse({
        'message': f'{role.capitalize()} {username} logged in successfully',
        'session':session.session_id,
        'role': role
    })
    response.set_cookie(cookie_name, session.session_id, httponly=True, secure=False, samesite='Lax', max_age=14400)

    return response


@csrf_exempt
def logout_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    if "SHOPKEEPER_SESSIONID" in request.COOKIES:
        session_id = request.COOKIES.get("SHOPKEEPER_SESSIONID")
        deleted_count = CustomSession.objects.filter(session_id=session_id, shopkeeper__isnull=False).delete()[0]
        response = JsonResponse({'message': f'Shopkeeper {request.shopkeeper.username} logged out successfully'} if deleted_count else {'error': 'No active session found'})
        response.delete_cookie("SHOPKEEPER_SESSIONID")
        return response

    elif "CUSTOMER_SESSIONID" in request.COOKIES:
        session_id = request.COOKIES.get("CUSTOMER_SESSIONID")
        deleted_count = CustomSession.objects.filter(session_id=session_id, customer__isnull=False).delete()[0]
        response = JsonResponse({'message': f'Customer {request.customer.username} logged out successfully'} if deleted_count else {'error': 'No active session found'})
        response.delete_cookie("CUSTOMER_SESSIONID")
        return response

    elif "SUPERUSER_SESSIONID" in request.COOKIES:
        session_id = request.COOKIES.get("SUPERUSER_SESSIONID")
        deleted_count = CustomSession.objects.filter(session_id=session_id, user__isnull=False).delete()[0]
        response = JsonResponse({'message': f'Superuser {request.user.username} logged out successfully'} if deleted_count else {'error': 'No active session found'})
        response.delete_cookie("SUPERUSER_SESSIONID")
        return response

    return JsonResponse({'error': 'No active session found'}, status=400)


@csrf_exempt
@timed_response
def active_user(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET method required'}, status=405)
    sessions = CustomSession.objects.filter(expires_at__gt=timezone.now()).select_related('customer', 'shopkeeper')
    users = []
    for s in sessions:
        if s.customer:
            users.append({'id': s.customer.id, 'username': s.customer.username, 'role': 'customer'})
        elif s.shopkeeper:
            users.append({'id': s.shopkeeper.id, 'username': s.shopkeeper.username, 'role': 'shopkeeper'})
        elif s.user:
            users.append({'id':s.user.id, 'username':s.user.username, 'role':'superuser'})
    if not users:
        return JsonResponse({'error':'No active users found'}, status=404)
    else:
        return {'active_user': users}



@csrf_exempt
def customer_registration(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    username = data.get('username')
    email = data.get('email')
    phone_number = data.get('phone_number')
    address = data.get('address')
    password = f'{username}{phone_number}'  
    
    if not username or not phone_number:
        return JsonResponse({'error': 'Username and phone number are required'}, status=400)
    
    existing_username = Customers.objects.filter(username=username, deleted_at__isnull=True).first()
    existing_phone_number = Customers.objects.filter(phone_number=phone_number, deleted_at__isnull=True).first()
    
    if existing_username:
        return JsonResponse({'error': 'Username already exists'}, status=400)
    
    if existing_phone_number:
        return JsonResponse({'error': 'Phone number already exists'}, status=400)
    
    soft_deleted = Customers.objects.filter(username=username, deleted_at__isnull=False).first()
    if soft_deleted:
        soft_deleted.deleted_at = None
        soft_deleted.email = email
        soft_deleted.phone_number = phone_number or soft_deleted.phone_number
        soft_deleted.address = address or soft_deleted.address
        if password:
            soft_deleted.password = make_password(password)
        soft_deleted.updated_at = timezone.now()
        soft_deleted.save()
        customer = soft_deleted
    else:
        customer = Customers.objects.create(
            username=username,
            email=email,
            phone_number=phone_number,
            address=address,
            role='customer',
            loyalyty_points=0,
            password=make_password(password)
        )
    
    return JsonResponse({
        'id': customer.id,
        'username': customer.username,
        'email': customer.email,
        'phone_number': customer.phone_number,
        'address': customer.address,
        'role': customer.role,
        'loyalyty_points': customer.loyalyty_points,
        'created_at': customer.created_at,
        'updated_at': customer.updated_at
    }, status=200)

    

@csrf_exempt
def shopkeeper_registration(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    user = _authorize_superuser(request)
    if not user:
        return JsonResponse({'error':'Only superuser can create shopkeeper accounts'}, status=403)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        phone_number = data.get('phone_number')
        shop_name = data.get('shop_name', None)
        address = data.get('address', None)
        is_verified = data.get('is_verified', False)
        rating = float(data.get('rating', 0.0))
    except Exception as e:
        return JsonResponse({'error': 'Invalid JSON or data', 'details': str(e)}, status=400)
    
    if not username or not phone_number:
        return JsonResponse({'error': 'Username and phone number is required'}, status=400)
    
    password = f'{username}{phone_number}'
    password = make_password(password)
    
    existing = Shopkeepers.objects.filter(username=username).first()
    if existing:
        if existing.deleted_at is None:
            return JsonResponse({'error': f'Shopkeeper {username} already exists'}, status=400)
        existing.deleted_at = None
        existing.email = email
        existing.phone_number = phone_number
        existing.shop_name = shop_name or existing.shop_name
        existing.address = address or existing.address
        existing.is_verified = is_verified
        existing.rating = rating
        existing.password = password
        existing.updated_at = timezone.now()
        existing.save()
        obj = existing
    else:
        obj = Shopkeepers.objects.create(
            username=username,
            password=password,
            email=email,
            phone_number = phone_number,
            shop_name=shop_name,
            address=address,
            is_verified=is_verified,
            rating=rating,
            role='shopkeeper'
        )
        obj.save()
    
    return JsonResponse({
        'id': obj.id,
        'username': obj.username,
        'email': obj.email, 
        'shop_name': obj.shop_name,
        'address': obj.address,
        'is_verified': obj.is_verified,
        'rating': obj.rating,
        'role': obj.role
    }, status=201)



@csrf_exempt
@timed_response
def search_product(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET method required'}, status=405)
    
    user = _authorize_shopkeeper(request) or _authorize_customer(request) or _authorize_superuser(request)
    if not user:
        print(user)
        return JsonResponse({'error': 'You should be an authorized user'}, status=401)

    name = request.GET.get('name', '').strip()
    page = request.GET.get('page', 1)
    try:
        page = int(page)                 
        if page < 1:
            page = 1
    except ValueError:
        page = 1                         
        
    if not name:
        return JsonResponse({'error': 'Product name required'}, status=400)

    cache_key = f'product_search_{name.lower()}'
    related_products = cache.get(cache_key)

    if not related_products:
        related_products = Products.objects.filter(name__icontains=name).values('name', 'price', 'stock').order_by('-price')
        if not related_products:
            return JsonResponse({'error': 'No products found for your search'}, status=404)
        cache.set(cache_key, list(related_products), timeout=300)

    products, total_pages = pagination_helper(related_products, page)
    if products is None:
        return JsonResponse({'error': f'Invalid page number, total pages are {total_pages}'}, status=400)

    return {
        'related_products': list(products),
        'current_page': page,
        'total_pages': total_pages,
        'total_products': len(related_products)
    }


@csrf_exempt
@timed_response
def create_product(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    shopkeeper = request.shopkeeper
    print(shopkeeper)
    if not shopkeeper:
        return JsonResponse({'error': 'Unauthorized: Only shopkeepers can create products'}, status=401)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    name = data.get('name')
    price = data.get('price')
    stock = data.get('stock', 0)
    description = data.get('description', '')
    discount_price = data.get('discount_price', None)
    category_name = data.get('category_name', None)

    if not name or not price:
        return JsonResponse({'error': 'Missing required fields: name or price'}, status=400)

    try:
        price = float(price)
        if discount_price is not None:
            discount_price = float(discount_price)
        stock = int(stock)
    except ValueError:
        return JsonResponse({'error': 'Invalid value for price, discount_price, or stock'}, status=400)

    category = None
    print(category)
    if category_name:
        print(category_name)
        from .models import Categories
        category = Categories.objects.filter(name=category_name).first()
        print('id:',category.id)
        if not category:
            Categories.objects.create(name=category_name)
            category = Categories.objects.filter(name=category_name).first()
            print(category.id)
            # return JsonResponse({'error': f'Category with name {category} does not exist'}, status=404)
            
    if Products.objects.filter(name=name, created_by=shopkeeper).exists():
        return JsonResponse({'error': f'Product {name} already exists for this shop'}, status=400)

    product_id = f'PRO-{uuid.uuid4().hex[:10]}'
    product = Products.objects.create(
        product_id = product_id,
        name=name,
        price=price,
        stock=stock,
        description=description,
        discount_price=discount_price,
        category=category,
        created_by=shopkeeper
    )

    return {
        'product_id': product_id,
        'name': product.name,
        'price': str(product.price),
        'discount_price': str(product.discount_price) if product.discount_price else None,
        'stock': product.stock,
        'category': product.category.id if product.category else None,
        'description': product.description,
        'created_by': product.created_by.username,
        'created_at': product.created_at.isoformat()
    }


@csrf_exempt
@timed_response
def list_categories(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET method required'}, status=405)
    
    page = request.GET.get('page', 1)
    try:
        page = int(page)
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    categories_qs = Categories.objects.annotate(
        product_count=Count('products')
    ).values('name', 'description', 'product_count').order_by('-product_count', 'name')

    categories_list = list(categories_qs)
    requested_categories, total_pages = pagination_helper(categories_list, page)
    if requested_categories is None:
        return JsonResponse({'error':f'Invalid page number, total pages are {total_pages}'})
    return {
        'categories': requested_categories,
        'current_page': page,
        'total_pages': total_pages,
        'total_categories': len(categories_list)
    }


@csrf_exempt
@timed_response
def list_products(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET method required'}, status=405)

    user = _authorize_shopkeeper(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)


    category_name = request.GET.get('category', None)
    search_name = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'created_at') 
    page = request.GET.get('page', 1)

    try:
        page = int(page)
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    qs = Products.objects.filter(created_by=user)

    if category_name:
        qs = qs.filter(category__name__iexact=category_name)

    if search_name:
        qs = qs.filter(name__icontains=search_name)

    sort_mapping = {
        'price_asc': 'price',
        'price_desc': '-price',
        'rating': '-rating',
        'stock': '-stock',
        'created_at': '-created_at',
    }
    qs = qs.order_by(sort_mapping.get(sort_by, '-created_at'))

    cache_key = f'products_user_{user.id}_cat_{category_name}_search_{search_name}_sort_{sort_by}_page_{page}'
    cached_products = cache.get(cache_key)
    if cached_products:
        products, total_pages, total_count = cached_products
        if products is None or page > total_pages:
            return JsonResponse({'error':f'Invalid page number, total pages {total_pages}'})
    else:
        products_list = list(qs.values('product_id', 'name', 'price', 'stock', 'rating', 'category__name'))
        products, total_pages = pagination_helper(products_list, page)
        total_count = len(products_list)
        cache.set(cache_key, (products, total_pages, total_count), timeout=300)
    if products is None or page > total_pages:
        return JsonResponse({'error':f'Invalid page number, total pages are {total_pages}'})

    return {
        'your_products': list(products),
        'current_page': page,
        'total_pages': total_pages,
        'total_products': total_count
    }


@csrf_exempt
@timed_response
def expensive_products(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET method required'}, status=405)

    user = _authorize_shopkeeper(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    page = request.GET.get('page', 1)
    category_name = request.GET.get('category', None)
    search_name = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'created_at')
    min_price = request.GET.get('min_price', None)
    max_price = request.GET.get('max_price', None)
    expensive = request.GET.get('expensive', True)

    try:
        page = max(int(page), 1)
    except ValueError:
        page = 1

    try:
        min_price = float(min_price) if min_price is not None else None
    except ValueError:
        min_price = None

    try:
        max_price = float(max_price) if max_price is not None else None
    except ValueError:
        max_price = None


    qs = Products.objects.filter(created_by=user)

    if category_name:
        qs = qs.filter(category__name__iexact=category_name)
    if search_name:
        qs = qs.filter(name__icontains=search_name)
    if min_price is not None:
        qs = qs.filter(price__gte=min_price)
    if max_price is not None:
        qs = qs.filter(price__lte=max_price)

    if expensive == True:
        threshold_price = 1000
        if min_price is None or min_price < threshold_price:
            min_price = threshold_price
        qs = qs.filter(price__gte=min_price)

        
    sort_mapping = {
        'price_asc': 'price',
        'price_desc': '-price',
        'rating': '-rating',
        'stock': '-stock',
        'created_at': '-created_at',
        }
    order_by = sort_mapping.get(sort_by, '-created_at')
    qs = qs.order_by(order_by)

    cache_key = (
        f'products_user_{user.id}_cat_{category_name}_search_{search_name}_'
        f'sort_{order_by}_min_{min_price}_max_{max_price}_exp_{expensive}_page_{page}'
    )
    cached_data = cache.get(cache_key)

    if cached_data:
        print('Cache Hit')
        products, total_pages, total_count = cached_data
        if products is None or page > total_pages:
            return JsonResponse({'error':f'Invalid page number, total pages {total_pages}'})
    else:
        print('Cache Miss')
        products_list = list(qs.values(
            'product_id', 'name', 'price', 'discount_price', 'stock', 'rating', 'category__name'
        ))
        products, total_pages = pagination_helper(products_list, page)
        if products is None or page > total_pages:
            return JsonResponse({'error':f'Invalid page number, total pages {total_pages}'}) 
        total_count = len(products_list)
        cache.set(cache_key, (products, total_pages, total_count), timeout=300)

    return {
        'your_products': list(products),
        'current_page': page,
        'total_pages': total_pages,
        'total_products': total_count,
        }


@csrf_exempt
@timed_response
def low_stock_products(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET method required'}, status=405)

    user = _authorize_shopkeeper(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    # Parameters
    page = request.GET.get('page', 1)
    try:
        page = max(int(page), 1)
    except ValueError:
        page = 1

    min_stock = request.GET.get('min_stock', 10)
    try:
        min_stock = int(min_stock)
    except ValueError:
        min_stock = 10

    cache_key = f'low_stock_user_{user.id}_max_{min_stock}_page_{page}'
    cached_data = cache.get(cache_key)

    if cached_data:
        print("Cache hit")
        products, total_pages, total_count = cached_data
        if products is None or page>total_pages:
            return JsonResponse({'error':f'Invalid page number, total pages are {total_pages}'})
    else:
        print("Cache miss")
        qs = Products.objects.filter(created_by=user, stock__lte=min_stock)
        products_list = list(qs.values('product_id', 'name', 'stock', 'category__name'))
        products, total_pages = pagination_helper(products_list, page)
        if products is None or page>total_pages:
            return JsonResponse({'error':f'Invalid page number, total pages are {total_pages}'})
        total_count = len(products_list)
        cache.set(cache_key, (products, total_pages, total_count), timeout=300)

    if not products:
        return {
            'low_stock_products': [],
            'current_page': page,
            'total_pages': total_pages,
            'total_products': total_count,
            'message': f'No low stock products found (stock <= {min_stock})'
        }

    return {
        'low_stock_products': list(products),
        'current_page': page,
        'total_pages': total_pages,
        'total_products': total_count
    }


@csrf_exempt
@timed_response
def top_selling_products(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET method required'}, status=405)

    user = _authorize_shopkeeper(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    page = request.GET.get('page', 1)
    category_name = request.GET.get('category', None)
    search_name = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'total_sold')
    top_n = request.GET.get('top_n', 10)

    try:
        page = max(int(page), 1)
    except ValueError:
        page = 1
    try:
        top_n = max(int(top_n), 10)
    except ValueError:
        top_n = 10

    qs = Orders.objects.filter(product__created_by=user)

    if category_name:
        qs = qs.filter(product__category__name__iexact=category_name)
    if search_name:
        qs = qs.filter(product__name__icontains=search_name)

    qs = qs.values(
        'product_id',
        'product__name',
        'product__price',
        'product__stock',
        'product__category__name'
    ).annotate(total_sold=Sum('quantity'))

    sort_mapping = {
        'total_sold': '-total_sold',
        'name': 'product__name',
        'price_asc': 'product__price',
        'price_desc': '-product__price',
        'stock': '-product__stock'
    }
    order_by = sort_mapping.get(sort_by, '-total_sold')
    qs = qs.order_by(order_by)
    
    cache_key = (
            f'top_selling_products_user_{user.id}_cat_{category_name}_search_{search_name}_'
            f'sort_{order_by}_topn_{top_n}_page_{page}'
        )
        
    cached_data = cache.get(cache_key)
    if cached_data:
        print('Cache Hit')
        requested_products, total_pages, total_count = cached_data
        if requested_products is None or page>total_pages:
            return JsonResponse({'error':f'Invalid page number, total pages are {total_pages}'})

    else:
        print('Cache Miss')
        products_list = list(qs[:top_n])
        total_count = len(products_list)
        requested_products, total_pages = pagination_helper(products_list, page)
    
        if not requested_products:
            return JsonResponse({
                'error': f'No products found or Invalid page number, total pages {total_pages}'
            }, status=404)

        
        cache.set(cache_key, (requested_products, total_pages, total_count), timeout=300)

    return {
        'top_selling_products': list(requested_products),
        'current_page': page,
        'total_pages': total_pages,
        'total_products': total_count,
        'top_n_limit': top_n
    }


@csrf_exempt
@timed_response
def place_order(request):
    if request.method not in ['POST', 'GET']:
        return JsonResponse({'error': 'POST or GET method required'}, status=405)

    user = _authorize_customer(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_name = data.get('product_name', '').strip()
            quantity = int(data.get('quantity', 1))
        except:
            return JsonResponse({'error': 'Invalid JSON or missing parameters'}, status=400)
    else:
        try:
            product_name = request.GET.get('product_name', '').strip()
            quantity = int(request.GET.get('quantity', 1))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Invalid product name or quantity'}, status=400)

    if not product_name:
        return JsonResponse({'error': 'Product name is required'}, status=400)

    try:
        product = Products.objects.get(name__iexact=product_name)
    except Products.DoesNotExist:
        return JsonResponse({'error': f'Product "{product_name}" not found'}, status=404)
    
    if product.stock < quantity:
        return JsonResponse({'error': 'Not enough stock', 'available_stock': product.stock}, status=400)

    order_id = f"ORD-{uuid.uuid4().hex[:10].upper()}"
    
    order = Orders.objects.create(
        order_id = order_id,
        customer=user,
        product=product,
        quantity=quantity,
        order_date=timezone.now()
    )

    product.stock -= quantity
    product.save(update_fields=['stock'])

    return {
        'order_id': order_id,
        'product': product.name,
        'quantity': quantity,
        'remaining_stock': product.stock,
        'customer': user.username,
        'order_date': order.order_date
    }


@csrf_exempt
@timed_response
def my_orders(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET method required'}, status=405)

    user = _authorize_customer(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    page = request.GET.get('page', 1)
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    sort_by = request.GET.get('sort', 'order_date')

    try:
        page = max(int(page), 1)
    except ValueError:
        page = 1

    qs = Orders.objects.filter(customer=user).select_related('product')

    if date_from:
        try:
            qs = qs.filter(order_date__gte=date_from)
        except:
            pass
    if date_to:
        try:
            qs = qs.filter(order_date__lte=date_to)
        except:
            pass

    sort_mapping = {
        'order_date': '-order_date',
        'quantity': '-quantity',
        'price_asc': 'product__price',
        'price_desc': '-product__price',
    }
    qs = qs.order_by(sort_mapping.get(sort_by, '-order_date'))

    cache_key = (
        f'my_orders_user_{user.id}_date_from_{date_from}_date_to_{date_to}_sort_{sort_by}_page_{page}'
    )
    cached_data = cache.get(cache_key)

    if cached_data:
        print("Cache hit")
        orders, total_pages, total_count = cached_data
        
    else:
        print("Cache miss")
        orders_list = list(qs.values(
            'order_id', 
            'product__name', 
            'quantity', 
            'product__price',
            'order_date',
            'product__category__name'
        ))
        orders, total_pages = pagination_helper(orders_list, page)
        total_count = len(orders_list)
        cache.set(cache_key, (orders, total_pages, total_count), timeout=300)

    if not orders:
        return JsonResponse({'error': f'No orders found or invalid page number, total pages are {total_pages}'}, status=404)

    return {
        'my_orders': list(orders),
        'current_page': page,   
        'total_pages': total_pages,
        'total_orders': total_count
    }


@csrf_exempt
@timed_response
def recent_orders(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET method required'}, status=405)

    user = _authorize_customer(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    page = request.GET.get('page', 1)
    sort_by = request.GET.get('sort', 'order_date') 

    try:
        page = max(int(page), 1)
    except ValueError:
        page = 1

    two_weeks_ago = timezone.now() - timedelta(days=14)
    qs = Orders.objects.filter(customer=user, order_date__gte= two_weeks_ago).select_related('product')

    sort_mapping = {
        'order_date': '-order_date',
        'quantity': '-quantity',
        'price_asc': 'product__price',
        'price_desc': '-product__price',
    }
    qs = qs.order_by(sort_mapping.get(sort_by, '-order_date'))

    cache_key = f'recent_orders_user_{user.id}_sort_{sort_by}_page_{page}'
    cached_data = cache.get(cache_key)
    if cached_data:
        print("Cache hit")
        orders, total_pages, total_count = cached_data
    else:
        print("Cache miss")
        orders_list = list(qs.values(
            'id', 'product__name', 'product__category__name', 'quantity', 'order_date', 'product__price'
        ))
        orders, total_pages = pagination_helper(orders_list, page)
        total_count = len(orders_list)
        cache.set(cache_key, (orders, total_pages, total_count), timeout=300)

    if not orders:
        return JsonResponse({'error': f'No orders found or invalid page number, total pages are {total_pages}'}, status=404)

    return {
        'recent_orders': list(orders),
        'current_page': page,
        'total_pages': total_pages,
        'total_orders': total_count
    }


@csrf_exempt
@timed_response
def orders_today(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET method required'}, status=405)

    user = _authorize_customer(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    page = request.GET.get('page', 1)
    sort_by = request.GET.get('sort', 'order_date')

    try:
        page = max(int(page), 1)
    except ValueError:
        page = 1

    today = timezone.now().date()
    qs = Orders.objects.filter(customer=user, order_date__date=today).select_related('product')

    sort_mapping = {
        'order_date': '-order_date',
        'quantity': '-quantity',
        'price_asc': 'product__price',
        'price_desc': '-product__price',
    }
    qs = qs.order_by(sort_mapping.get(sort_by, '-order_date'))

    cache_key = f'orders_today_user_{user.id}_sort_{sort_by}_page_{page}'
    cached_data = cache.get(cache_key)
    if cached_data:
        print("Cache hit")
        orders, total_pages, total_count = cached_data
    else:
        print("Cache miss")
        orders_list = list(qs.values(
            'id', 'product__name', 'product__category__name', 'quantity', 'order_date', 'product__price'
        ))
        orders, total_pages = pagination_helper(orders_list, page)
        total_count = len(orders_list)
        cache.set(cache_key, (orders, total_pages, total_count), timeout=300)

    if not orders:
        return JsonResponse({'error': f'No orders found or invalid page number, total pages are {total_pages}'}, status=404)

    return {
        'today_orders': list(orders),
        'current_page': page,
        'total_pages': total_pages,
        'total_orders': total_count
    }