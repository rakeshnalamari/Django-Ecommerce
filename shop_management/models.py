from django.contrib.auth.models import User
from django.db import models
import uuid
from django.utils import timezone

# def random_mobile_number():
#     return str(random.choice([6,7,8,9])) + ''.join([str(random.randint(0,9)) for _ in range(9)])


class Shopkeepers(models.Model):
    role = models.CharField(max_length=20, default='shopkeeper')
    username = models.CharField(max_length=50, db_index=True)
    shop_name = models.CharField(max_length=100,null=True, blank=True)
    rating = models.FloatField(default=0.0)
    phone_number = models.BigIntegerField(unique = True)
    password = models.CharField(max_length=128, null=True, blank=True) 
    email = models.CharField(unique=True, max_length=100)
    address = models.TextField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'shopkeepers'
        indexes = [models.Index(fields=['username'])]
    
    def __str__(self):
        return f'{self.username}-{self.shop_name}'


class Customers(models.Model):
    role = models.CharField(max_length=20, default='customer')
    username = models.CharField(max_length=50, db_index=True)
    phone_number = models.BigIntegerField(unique=True) 
    email = models.CharField(unique=True, max_length=100)
    password = models.CharField(max_length=128, null=True, blank=True)  
    loyalyty_points = models.IntegerField(default=0)
    address = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'customers'
        indexes = [models.Index(fields=['username', 'email'])]

    def __str__(self):
        return self.username


class Categories(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, default= "No description about this category")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Products(models.Model):
    product_id = models.CharField(max_length=15, unique=True, null=True, blank=True)
    name = models.CharField(max_length=100, db_index=True)
    category = models.ForeignKey('Categories', on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    total_sold = models.IntegerField(default=0)
    stock = models.IntegerField(default=0)
    created_by = models.ForeignKey('Shopkeepers', on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        db_table = 'products'
        indexes = [
            models.Index(fields=['name', 'price']),
            models.Index(fields=['category']),
        ]
        unique_together = ('name', 'created_by')

    def __str__(self):
        return f"{self.category.name if self.category else 'No Category'} - {self.name}"


class Orders(models.Model):
    id = models.BigAutoField(primary_key=True)
    order_id = models.CharField(max_length=15, unique=True, null=True, blank=True)
    customer = models.ForeignKey(Customers, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Products, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.IntegerField()
    order_date = models.DateTimeField(blank=True, null=True, db_index=True)
    status = models.CharField(max_length=20, default='pending')
    shipping_address = models.TextField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'orders'
        indexes = [
            models.Index(fields=['customer', 'product']),
            models.Index(fields=['order_date']),
        ]

    def __str__(self):
        return f"Ordered #{self.product.name} by {self.customer.username}"


class CustomSession(models.Model):
    session_id = models.CharField(max_length=64, unique=True, default=str(uuid.uuid4()))
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    customer = models.ForeignKey(Customers, on_delete=models.CASCADE, null=True, blank=True)
    shopkeeper = models.ForeignKey(Shopkeepers, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_activity = models.DateTimeField(auto_now=True)
    
    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        if self.customer:
            return f"Session {self.session_id} for {self.customer.username}"
        if self.shopkeeper:
            return f"Session {self.session_id} for {self.shopkeeper.username}"
        return f"Session {self.session_id} (no user)"

class Reviews(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(Customers, on_delete=models.CASCADE)
    rating = models.DecimalField(max_digits=3, decimal_places=2)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('product', 'customer')

    def __str__(self):
        return f"Review by {self.customer.username} for {self.product.name} ({self.rating}/5)"

        
class Carts(models.Model):
    customer = models.ForeignKey(Customers, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.__class__.__name__} for {self.customer.username}"


class CartItems(models.Model):
    cart = models.ForeignKey(Carts, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    
    def __str__(self):
        return f"{self.__class__.__name__} for {self.customer.username}"

    
class Wishlists(models.Model):
    customer = models.ForeignKey(Customers, on_delete=models.CASCADE)
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('customer', 'product')
    def __str__(self):
        return f"{self.__class__.__name__} for {self.customer.username}"

class Promotions(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    discount_percentage = models.IntegerField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    def __str__(self):
        return f"{self.__class__.__name__} for {self.customer.username}"

class Notifications(models.Model):
    customer = models.ForeignKey(Customers, on_delete=models.CASCADE) 
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.__class__.__name__} for {self.customer.username}"
