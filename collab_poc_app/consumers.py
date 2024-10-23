
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from collab_poc_app.models import TestDoc
from pycrdt_model.consumers import YjsUpdateConsumer

class TestDocUpdateConsumer(YjsUpdateConsumer[TestDoc]):
    def __init__(self, worker_channel_name: str):
        super().__init__(TestDoc, worker_channel_name)

    async def get_ydoc_model_object(self) -> TestDoc | None:
        user: User | None = self.scope["user"]
        if user is None or user.is_anonymous:
            await self.close(code=503)
            return None
        try:
            return await TestDoc.objects.aget(pk=self.scope["url_route"]["kwargs"]["pk"])
        except TestDoc.DoesNotExist:
            await self.close(code=404)
            return None
