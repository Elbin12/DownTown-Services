from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from accounts.models import CustomUserManager, CustomUser
from admin_auth.models import Categories, SubCategories

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

    def __str__(self):
        return str(self.user.email)
    

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
    