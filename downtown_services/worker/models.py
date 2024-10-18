from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from accounts.models import CustomUserManager
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
    user = models.OneToOneField(CustomWorker, on_delete = models.CASCADE, related_name = 'worker_profile' )
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    profile_pic = models.ImageField(upload_to = 'worker/profile_pic/', null=True, blank=True)

    def __str__(self):
        return str(self.user.email)
    

class Services(models.Model):
    worker = models.ForeignKey(CustomWorker, on_delete=models.CASCADE, related_name='services')
    service_name = models.CharField()
    description = models.TextField()
    category = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name='services')
    subcategory = models.ForeignKey(SubCategories, on_delete=models.CASCADE, related_name='services')
    pic =  models.ImageField(upload_to = 'services/', null=True, blank=True)    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    price = models.IntegerField()
    # is_approved = models.BooleanField(default=False)