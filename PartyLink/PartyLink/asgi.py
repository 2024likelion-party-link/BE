from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from room.routing import websocket_urlpatterns as room_websocket
from chat.routing import websocket_urlpatterns as chat_websocket
from handGame.routing import websocket_urlpatterns as game_websocket
from django.core.asgi import get_asgi_application
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PartyLink.settings')


application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                room_websocket + chat_websocket+game_websocket
            )
        )
    ),
})
