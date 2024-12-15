from django.urls import path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    path('ws/chat/<str:room_id>/', ChatConsumer.as_asgi()),
]  # 대괄호가 제대로 닫혔는지 확인
