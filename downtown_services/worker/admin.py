from django.contrib import admin
from .models import CustomWorker, WorkerProfile, Services

# Register your models here.
admin.site.register(CustomWorker)
admin.site.register(WorkerProfile)
admin.site.register(Services)