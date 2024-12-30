from django.db import models

# Create your models here.


class Categories(models.Model):
    category_name = models.CharField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class SubCategories(models.Model):
    subcategory_name = models.CharField()
    category = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name='subcategories')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Subscription(models.Model):
    ANALYTICS_CHOICES = [
        ('no_analytics', 'No Analytics'),
        ('basic', 'Basic'),
        ('advanced', 'Advanced'),
    ]
    stripe_price_id = models.CharField(max_length=255, unique=True, null=True)
    stripe_product_id = models.CharField(max_length=255, unique=True, null=True) 
    tier_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    platform_fee_perc = models.IntegerField(default=1)
    service_add_limit = models.CharField(max_length=20, default='0')
    service_update_limit = models.CharField(max_length=20, default='0')
    user_requests_limit = models.CharField(max_length=20, default='0')
    analytics = models.CharField(max_length=20, choices=ANALYTICS_CHOICES, default='no_analytics')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.tier_name