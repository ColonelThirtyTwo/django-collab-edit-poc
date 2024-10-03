from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/doc/(?P<pk>[0-9]+)$", consumers.PocYjsConsumer.as_asgi()),
]
