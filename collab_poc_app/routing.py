from django.urls import re_path

from collab_poc_app.models import TestDoc
from pycrdt_model.consumers import YjsUpdateConsumer, DEFAULT_WORKER_CHANNEL_NAME

websocket_urlpatterns = [
    re_path(r"ws/doc/(?P<pk>[0-9]+)$", YjsUpdateConsumer.as_asgi(
        model=TestDoc,
        worker_channel_name=DEFAULT_WORKER_CHANNEL_NAME,
    )),
]
