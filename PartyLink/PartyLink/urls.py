from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', views.health_check, name='health_check'),
    path('rooms/', include('room.urls')),  # room 앱의 urls.py와 연결
    path('chat/', include('chat.urls')),  # chat 앱의 urls.py와 연결
    path('handgame/', include('handGame.urls')),  # handGame 앱의 urls.py와 연결
]
