from django.contrib import admin
from .models import CustomWorker, WorkerProfile

# Register your models here.
admin.site.register(CustomWorker)
admin.site.register(WorkerProfile)