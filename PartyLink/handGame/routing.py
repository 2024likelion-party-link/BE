from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/handgame/<uuid:room_id>/', consumers.HandGameConsumer.as_asgi()),
]
