# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# from channels.security.websocket import AllowedHostsOriginValidator
# from room.routing import websocket_urlpatterns as room_websocket
# from chat.routing import websocket_urlpatterns as chat_websocket
# from django.core.asgi import get_asgi_application
# import os

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PartyLink.settings')


# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AllowedHostsOriginValidator(
#         AuthMiddlewareStack(
#             URLRouter(
#                 room_websocket + chat_websocket
#             )
#         )
#     ),
# })
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from chat.routing import websocket_urlpatterns as chat_websocket_urlpatterns
from room.routing import websocket_urlpatterns as room_websocket_urlpatterns
from handGame.routing import websocket_urlpatterns as handgame_websocket_urlpatterns
from django.core.asgi import get_asgi_application
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PartyLink.settings')


application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chat_websocket_urlpatterns +
            room_websocket_urlpatterns +
            handgame_websocket_urlpatterns
        )
    ),
})