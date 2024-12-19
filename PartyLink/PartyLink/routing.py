from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from chat.routing import websocket_urlpatterns as chat_websocket_urlpatterns
from handGame.routing import websocket_urlpatterns as handgame_websocket_urlpatterns
from room.routing import websocket_urlpatterns as room_websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chat_websocket_urlpatterns +
            handgame_websocket_urlpatterns +
            room_websocket_urlpatterns
        )
    ),
})
