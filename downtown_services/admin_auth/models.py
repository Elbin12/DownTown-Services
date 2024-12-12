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
    tier_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.tier_name


class SubscriptionFeatures(models.Model):
    ANALYTICS_CHOICES = [
        ('no_analytics', 'No Analytics'),
        ('basic', 'Baisc'),
        ('advanced', 'Advanced'),
    ]
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='subscription_features')
    platform_fee_perc = models.IntegerField()
    service_add_count = models.CharField(max_length=20, default='0')
    service_update_count = models.CharField(max_length=20, default='0')
    user_requests_count = models.CharField(max_length=20, default='0')
    analytics = models.CharField(max_length=20, choices=ANALYTICS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subscription.tier_name} Features"