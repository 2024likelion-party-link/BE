from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chat/', include('chat.urls')),  # chat 앱의 urls 포함
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)