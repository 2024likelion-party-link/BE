from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('rooms/', include('room.urls')),  # room 앱의 urls.py와 연결
]
