from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from accounts.models import CustomUserManager, CustomUser
from admin_auth.models import Categories, SubCategories, Subscription
import uuid

# Create your models here.


    
class CustomWorker(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    mob = models.CharField(max_length=10, unique=True)
    is_staff = models.BooleanField(default=True)
    is_active = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    STATUS_CHOICES = [
        ('in_review', 'In Review'),
        ('rejected', 'Rejected'),
        ('verified', 'Verified'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_review')
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customworker_groups', 
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customworker_permissions', 
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.email
    

class WorkerProfile(models.Model):
    user = models.OneToOneField(CustomWorker, on_delete = models.CASCADE, related_name = 'worker_profile')
    first_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    profile_pic = models.ImageField(upload_to = 'worker/profile_pic/', null=True, blank=True)
    users = models.ManyToManyField(CustomUser, through='Requests', related_name='workers')
    location = models.CharField(max_length=255, null=True, blank=True)
    lat = models.DecimalField(max_digits=25, decimal_places=20)
    lng = models.DecimalField(max_digits=25, decimal_places=20) 
    aadhaar_no = models.CharField(max_length=12, null=True, blank=True)
    experience = models.IntegerField(null=True, blank=True)
    certificate = models.ImageField(upload_to = 'worker/certificate/', null=True, blank=True)
    services = models.ManyToManyField(Categories, related_name='workers')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='worker_profile', null=True, blank=True)
    is_subscribed = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return str(self.user.email)

class WorkerSubscription(models.Model):
    SUBSCRIPTION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('expired', 'Expired'),
        ('past_due', 'Past Due'),
    ]

    worker_profile = models.OneToOneField(WorkerProfile, on_delete=models.CASCADE, related_name='worker_subscription')
    stripe_subscription_id = models.CharField(max_length=100, null=True, blank=True)
    invoice_id = models.CharField(max_length=255, null=True, blank=True)

    #subscription details
    stripe_price_id = models.CharField(max_length=255, null=True)
    stripe_product_id = models.CharField(max_length=255, null=True) 
    tier_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    #subscription features
    platform_fee_perc = models.IntegerField(default=1)
    analytics = models.CharField(max_length=20)
    service_add_limit = models.IntegerField(default=0)
    service_update_limit = models.IntegerField(default=0)
    user_requests_limit = models.IntegerField(default=0)

    subscription_status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS_CHOICES,
        default='expired'
    )
    subscription_start_date = models.DateTimeField(auto_now_add=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)

    services_added = models.IntegerField(default=0)
    services_updated = models.IntegerField(default=0)
    user_requests_handled = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def can_add_service(self):
        """Check if the worker can add more services."""
        if self.subscription_status != 'expired':
            return self.services_added < self.service_add_limit
        return False

    def can_update_service(self):
        """Check if the worker can update more services."""
        if self.subscription_status != 'expired':
            return self.services_updated < self.service_update_limit
        return False

    def can_handle_request(self):
        """Check if the worker can handle more user requests."""
        if self.subscription_status != 'expired':
            return self.user_requests_handled < self.user_requests_limit
        return False

    def increment_services_added(self):
        """Increment the count of services added if within the limit."""
        if self.can_add_service():
            self.services_added += 1
            self.save()
        else:
            raise ValueError("Service addition limit reached for the subscription tier.")

    def increment_services_updated(self):
        """Increment the count of services updated if within the limit."""
        if self.can_update_service():
            self.services_updated += 1
            self.save()
        else:
            raise ValueError("Service update limit reached for the subscription tier.")

    def increment_user_requests_handled(self):
        """Increment the count of user requests handled if within the limit."""
        if self.can_handle_request():
            self.user_requests_handled += 1
            self.save()
        else:
            raise ValueError("User request handling limit reached for the subscription tier.")

    def reset_usage_counts(self):
        """Reset all usage counts at the start of a new billing cycle."""
        self.services_added = 0
        self.services_updated = 0
        self.user_requests_handled = 0
        self.save()


class Services(models.Model):
    worker = models.ForeignKey(CustomWorker, on_delete=models.CASCADE, related_name='services')
    service_name = models.CharField()
    description = models.TextField()
    category = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name='services')
    subcategory = models.ForeignKey(SubCategories, on_delete=models.CASCADE, related_name='services')
    pic =  models.FileField(upload_to = 'services/', null=True, blank=True)    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    price = models.IntegerField()
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    is_listed = models.BooleanField(default=True)
    
class Requests(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='request')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='request')
    service = models.ForeignKey(Services, on_delete=models.CASCADE, related_name='request')
    description = models.TextField()
    STATUS_CHOICES = [
        ('request_sent', 'Request Sent'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='request_sent')
    created_at = models.DateTimeField(default=timezone.now)
    is_completed = models.BooleanField(default=False)

class Wallet(models.Model):
    wallet_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    worker = models.ForeignKey(CustomWorker, on_delete=models.CASCADE, related_name='wallet')
    balance = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def add_balance(self, amount):
        self.balance += amount
        self.save()

    def deduct_balance(self, amount):
        if amount <= self.balance:
            self.balance -= amount
            self.save()
        else:
            raise ValueError("Insufficient balance")

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]

    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, 
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], 
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.status == 'completed':
            if self.transaction_type == 'credit':
                self.wallet.add_balance(self.amount)
            elif self.transaction_type == 'debit':
                self.wallet.deduct_balance(self.amount)
    