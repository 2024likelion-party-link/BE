from django.urls import path
from .views import *

urlpatterns = [
    path('create-room/', CreateRoomView.as_view(), name='create-room'),
    path('games/', GetGamesView.as_view(), name='get_games'),
    path('<str:room_id>/info/', GetRoomInfoView.as_view(), name='get_room_info'),
]