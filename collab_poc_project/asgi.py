"""
ASGI config for project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter, ChannelNameRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'collab_poc_project.settings')
django_asgi_app = get_asgi_application()

from collab_poc_app.routing import websocket_urlpatterns
from pycrdt_model.consumers import YjsSaverWorkerConsumer, DEFAULT_WORKER_CHANNEL_NAME

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(websocket_urlpatterns))),
    "channel": ChannelNameRouter({
        DEFAULT_WORKER_CHANNEL_NAME: YjsSaverWorkerConsumer.as_asgi(),
    }),
})
