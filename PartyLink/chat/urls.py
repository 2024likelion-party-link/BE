from django.urls import path
from .views import MessageView

urlpatterns = [
    path("rooms/<uuid:room_id>/messages/", MessageView.as_view(), name="room-messages"),
]

