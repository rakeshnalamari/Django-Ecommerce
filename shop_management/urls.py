from django.urls import path
from . import views
from . import helpers

urlpatterns = [

    path('fetch_responses/', helpers.fetch_multiple_requests, name='fetch_multiple_apis_post'),
    
    # LOGIN / SESSION
    
    path('login/', views.login_view, name="login_view"),
    path('active/', views.active_user, name='active_users'),
    path('logout/', views.logout_view, name='logout'),
    path('categories/',views.list_categories,name= 'list_categories'),
    
    # USERS (creation)
    path('customers/register/', views.customer_registration, name='customer_registration'),
    path('shopkeepers/register/', views.shopkeeper_registration, name='shopkeeper_registration'),

    # PRODUCTS (Shopkeeper only)
    path('products/search/', views.search_product, name ='search_product'),
    path('products/create/', views.create_product, name='create_product'),
    path('list_products/', views.list_products, name='list_products'),
    path('products/expensive/', views.expensive_products, name='expensive_products'),
    path('products/low-stock/', views.low_stock_products, name='low_stock_products'),
    path('products/top-selling/', views.top_selling_products, name='top_selling_products'),

    # ORDERS (Customer only)
    path('orders/create/', views.place_order, name='place_order'),
    path('list_orders/', views.my_orders, name='my_orders'),
    path('orders/today/', views.orders_today, name='orders_today'),
    path('orders/recent/', views.recent_orders, name='recent_orders'),
    
]
