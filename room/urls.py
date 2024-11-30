from django.urls import path
from .views import CreateRoomView, JoinRoomView

urlpatterns = [
    path('create/', CreateRoomView.as_view(), name='create_room'),
    path('<str:room_code>/', JoinRoomView.as_view(), name='join_room'),
]
