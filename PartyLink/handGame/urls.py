from django.urls import path
from .views import HandGameStartAPIView, HandGameEndAPIView

urlpatterns = [
    path('start/<str:room_id>/', HandGameStartAPIView.as_view(), name='start-game'),
    path('end/<str:room_id>/', HandGameEndAPIView.as_view(), name='end-game'),
]
