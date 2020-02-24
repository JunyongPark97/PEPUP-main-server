from channels.routing import ProtocolTypeRouter, URLRouter
from pepup.utils import TokenAuthMiddlewareStack
from channels.auth import AuthMiddlewareStack

import chat.routing

# 클라이언트와 Channels 개발 서버가 연결 될 때, 어느 protocol 타입의 연결인지
application = ProtocolTypeRouter({
    # (http->django views is added by default)
    'websocket': AuthMiddlewareStack(
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ),
})
