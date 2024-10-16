"""
URL configuration for downtown_services project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from . import views


urlpatterns = [
    path('signup/', views.SignUp.as_view()),
    path('login/', views.Login.as_view()),
    path('profile/', views.Profile.as_view()),
    path('logout/', views.Logout.as_view()),
    path('check-credentials/', views.CheckingCredentials.as_view()),
    path('services/', views.ServicesManage.as_view()),
    path('services/<int:pk>/', views.ServicesManage.as_view(), name='services-edit'),
]
