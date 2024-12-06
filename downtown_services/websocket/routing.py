from django.urls import re_path
from .consumers import NotificationConsumer, ChatConsumer

websocket_urlpatterns = [
    re_path(r'^ws/notification/(?P<user_id>\w+)/$', NotificationConsumer.as_asgi()),
    re_path(r'^ws/chat/(?P<role>\w+)/(?P<user_id>\w+)/(?P<worker_id>\w+)/$', ChatConsumer.as_asgi()),
]