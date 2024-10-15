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


class Services(models.Model):
    service_name = models.CharField()
    description = models.TextField()
    category = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name='services')
    subcategory = models.ForeignKey(SubCategories, on_delete=models.CASCADE, related_name='services')
    pic =  models.ImageField(upload_to = 'services/', null=True, blank=True)    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)