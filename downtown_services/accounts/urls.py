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
from django.urls import path
from . import views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
   path('signin/', views.SignIn.as_view()),
   path('signin-with-google/',views.SignInWithGoogle.as_view()),
   path('sent-otp/', views.SentOTP.as_view()),
   path('verify_otp/', views.VerifyOTP.as_view()),
   path('verify/', views.Verify.as_view()),
   path('logout/', views.LogoutView.as_view()),
   path('profile/', views.Profile.as_view()),
   path('change-location/', views.ChangeLocation.as_view()),
   path('categories/', views.GetCategories.as_view()),
   path('services/', views.ServicesView.as_view()),
   path('service/<int:pk>/', views.ServiceDetail.as_view()),
   path('service-request/', views.ServiceRequests.as_view()),
   path('cancel-request/', views.CancelRequest.as_view()),
   path('find-order/<int:pk>/', views.FindOrderFromRequest.as_view()),
   path('worker-arrived/', views.WorkerArrived.as_view()),
   path('orders/', views.OrdersView.as_view()),
   path('order/<int:pk>/', views.OrderView.as_view()),
   path('order/<int:pk>/report/', views.ReportOrder.as_view()),
   path('create_payment/', views.CreatePayment.as_view()),
   path('payment-success/<int:pk>/', views.PaymentSuccess.as_view()),
   path('add-review/', views.AddReview.as_view()),
   path('add-interactions/', views.update_interaction.as_view()),
   path('wallet/', views.WalletView.as_view()),
   path('add-money/', views.WalletView.as_view()),
   path('capture_payment/', views.CapturePayment.as_view()),
   path('chat/history/<int:user_id>/<int:worker_id>/<int:page_no>/', views.ChatHistoryView.as_view(), name='chat-history'),
   path('chats/', views.Chats.as_view()),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)