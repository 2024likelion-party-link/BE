from django.urls import path
from .views import StartGameAPIView, SubmitActionAPIView, GameStatusAPIView

urlpatterns = [
    path('start/<uuid:room_id>/', StartGameAPIView.as_view(), name='start_game'),
    path('submit/<uuid:room_id>/', SubmitActionAPIView.as_view(), name='submit_action'),
    path('status/<uuid:room_id>/', GameStatusAPIView.as_view(), name='game_status'),
]
