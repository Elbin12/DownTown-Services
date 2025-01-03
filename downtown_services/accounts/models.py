from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils import timezone
import uuid

# Create your models here.


class CustomUserManager(BaseUserManager):
    def create_user(self, email=None, mob=None, password=None, **extra_fields):
        if not email and not mob:
            raise ValueError('Email or Mobile number is required')
        email = self.normalize_email(email)
        user = self.model(
            email = email,
            mob = mob,
            **extra_fields
        )
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, mob=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(email, mob, password, **extra_fields)

    
class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, null=True, blank=True)
    mob = models.CharField(max_length=10, unique=True, null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    location = models.CharField(max_length=255, null=True)
    lat = models.DecimalField(max_digits=25, decimal_places=20, null=True)
    lng = models.DecimalField(max_digits=25, decimal_places=20, null=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_groups', 
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions', 
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete = models.CASCADE, related_name = 'user_profile' )
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    profile_pic = models.FileField(upload_to = 'users/profile_pic/', null=True, blank=True)
    is_any_pending_payment = models.BooleanField(default=False)

    def __str__(self):
        return str(self.user.email)
        

class Orders(models.Model):
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='orders')
    service_provider = models.ForeignKey('worker.CustomWorker', on_delete=models.CASCADE, related_name='serviced_orders')
    request = models.ForeignKey('worker.Requests', on_delete=models.CASCADE, related_name='service_request')

    service_name = models.CharField(max_length=255)
    service_description = models.TextField()
    service_price = models.DecimalField(max_digits=10, decimal_places=2)
    service_image_url = models.URLField(max_length=500)

    otp = models.IntegerField()

    user_description = models.TextField(null=True)

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('working', 'Working'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

class OrderTracking(models.Model):
    order = models.OneToOneField(Orders, on_delete=models.CASCADE, related_name='status_tracking')
    is_worker_arrived = models.BooleanField(default=False)
    is_work_started = models.BooleanField(default=False)
    arrival_time = models.DateTimeField(null=True, blank=True) 
    work_start_time = models.DateTimeField(null=True, blank=True) 
    work_end_time = models.DateTimeField(null=True, blank=True)
    
class OrderPayment(models.Model):
    order = models.OneToOneField(Orders, on_delete=models.CASCADE, related_name='order_payment')
    total_amount = models.IntegerField(null=True, blank=True)
    STATUS_CHOICES = [
        ('unPaid', 'UnPaid'),
        ('paid', 'Paid'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unPaid')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    

class Additional_charges(models.Model):
    order_payment = models.ForeignKey(OrderPayment, on_delete=models.CASCADE, related_name='additional_charges')
    description = models.TextField()
    price = models.IntegerField()
    image = models.FileField(upload_to = 'users/payment/receipts/', null=True, blank=True)

class Review(models.Model):
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, related_name='review')
    review = models.CharField(max_length=200)
    rating = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review by {self.user} for {self.order} - Rating: {self.rating}"

class Interactions(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='interactions')
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='interactions')
    is_liked = models.BooleanField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Wallet(models.Model):
    wallet_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='wallet')
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



class ChatMessage(models.Model):
    sender_type_choices = (
        ('user', 'User'),
        ('worker', 'Worker'),
    )
    sender_id = models.IntegerField()
    sender_type = models.CharField(max_length=10, choices=sender_type_choices)
    recipient_id = models.IntegerField()
    recipient_type = models.CharField(max_length=10, choices=sender_type_choices)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    # is_read = models.BooleanField(default=False)