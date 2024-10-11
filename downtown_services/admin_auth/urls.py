from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
   path('login/', views.Login.as_view()),
   path('users/', views.Users.as_view()),
   path('block/', views.Block.as_view()),
   path('workers/', views.Workers.as_view()),
   path('requests/', views.Requests.as_view()),
   path('handle_requests/', views.HandleRequest.as_view()),
]