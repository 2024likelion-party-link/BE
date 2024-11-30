from django.urls import path
from .views import CreateRoomView, JoinRoomView, GetParticipantsView

urlpatterns = [
    path('create-room/', CreateRoomView.as_view(), name='create-room'),
    path('join-room/<uuid:room_id>/', JoinRoomView.as_view(), name='join-room'),
    path('participants/<uuid:room_id>/', GetParticipantsView.as_view(), name='get-participants'),
]
