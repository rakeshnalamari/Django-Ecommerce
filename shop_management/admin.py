from django.contrib import admin
from .models import Customers, Shopkeepers, Products, Orders, Carts, CartItems,Categories, Reviews, Wishlists, Promotions, Notifications

# Register your models here.
admin.site.register(Shopkeepers)
admin.site.register(Customers)
admin.site.register(Products)
admin.site.register(Orders)
admin.site.register(Carts)
admin.site.register(CartItems)
admin.site.register(Categories)
admin.site.register(Reviews)
admin.site.register(Wishlists)
admin.site.register(Promotions)
admin.site.register(Notifications)