from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
   path('login/', views.Login.as_view()),
   path('users/', views.Users.as_view()),
   path('block/', views.Block.as_view()),
   path('block-worker/', views.WorkerBlock.as_view()),
   path('workers/', views.Workers.as_view()),
   path('worker/<int:pk>/', views.Worker.as_view()),
   path('requests/', views.Requests.as_view()),
   path('handle_requests/', views.HandleRequest.as_view()),
   path('services/', views.GetServices.as_view()),
   path('service/<int:pk>/', views.GetService.as_view()),
   path('categories/', views.CategoryManage.as_view(), name='category-list'),
   path('categories/<int:pk>/', views.CategoryManage.as_view(), name='category-edit'),
   path('subcategories/', views.Subcategory.as_view(), name='subcategory-list'),
   path('subcategories/<int:pk>/', views.Subcategory.as_view(), name='subcategory-edit'),
   path('subscriptions/', views.SubscriptionsView.as_view()),
   path('subscription/<int:pk>/', views.SubscriptionsView.as_view()),
   path('orders/', views.GetOrders.as_view()),
   path('order/<int:pk>/', views.GetOrderDetails.as_view()),
]