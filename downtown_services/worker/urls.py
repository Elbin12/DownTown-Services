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
    path('subscription_plans/', views.SubscriptionPlans.as_view()),
    path('subscription/create/', views.CreateSubscriptionView.as_view()),
    path("subscription/upgrade/", views.SubscriptionUpgrade.as_view()),
    path("subscription/cancel/", views.CancelSubscription.as_view()),
    path('signup/', views.SignUp.as_view()),
    path('login/', views.Login.as_view()),
    path('profile/', views.Profile.as_view()),
    path('change-location/', views.ChangeLocation.as_view()),
    path('logout/', views.Logout.as_view()),
    path('check-credentials/', views.CheckingCredentials.as_view()),
    path('services/', views.ServicesManage.as_view()),
    path('services/<int:pk>/', views.ServicesManage.as_view(), name='services-edit'),
    path('requests/', views.WorkerRequests.as_view()),
    path('accepted-requests/', views.AcceptedServices.as_view()),
    path('accepted-service/<int:pk>/', views.AcceptedService.as_view()),
    path('check-otp/', views.CheckOTP.as_view()),
    path('orders/', views.OrdersView.as_view()),
    path('work-completed/', views.WorkCompleted.as_view()),
    path('add-payment/', views.AddPayment.as_view()),
    path('chat/history/<int:user_id>/<int:worker_id>/<int:page_no>/', views.ChatHistoryView.as_view(), name='chat-history'),
    path('chats/', views.Chats.as_view()),
    path('wallet/', views.WalletView.as_view()),
    path('add-money/', views.WalletView.as_view()),
    path('capture_payment/', views.CapturePayment.as_view()),
    path('dashboard/', views.Dashboard.as_view()),
    path("categories/", views.GetCategories.as_view()),
]
