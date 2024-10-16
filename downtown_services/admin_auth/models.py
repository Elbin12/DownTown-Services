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


