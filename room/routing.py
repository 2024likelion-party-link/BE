from django.urls import path
from .consumers import GameConsumer

websocket_urlpatterns = [
    path('ws/game/<uuid:room_id>/', GameConsumer.as_asgi()),
]
