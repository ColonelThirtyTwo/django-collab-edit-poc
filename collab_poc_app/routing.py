from django.urls import re_path

from collab_poc_app.consumers import TestDocUpdateConsumer
from pycrdt_model.consumers import DEFAULT_WORKER_CHANNEL_NAME

websocket_urlpatterns = [
    re_path(
        r"ws/doc/(?P<pk>[0-9]+)$",
        TestDocUpdateConsumer.as_asgi(
            worker_channel_name=DEFAULT_WORKER_CHANNEL_NAME,
        ),
    ),
]
