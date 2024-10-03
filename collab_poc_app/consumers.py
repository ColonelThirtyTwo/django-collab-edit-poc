
import asyncio
from typing import Any, Callable, Coroutine
import uuid
import logging
from django.shortcuts import aget_object_or_404
from django.db import transaction
from django.contrib.auth.models import User
import pycrdt
from pycrdt_websocket.django_channels_consumer import YjsConsumer
from channels.consumer import AsyncConsumer
from channels.layers import BaseChannelLayer
from channels.db import database_sync_to_async

from collab_poc_app.models import TestDoc

logger = logging.getLogger(__name__)

class PocYjsConsumer(YjsConsumer):

    connection_id: str
    updates_to_send: list[Any]

    def __init__(self):
        super().__init__()
        self.connection_id = str(uuid.uuid4())
        self.updates_to_send = []

    async def connect(self):
        user: User | None = self.scope["user"]
        if user is None or user.is_anonymous:
            await self.close(code=503)
            return
        return await super().connect()

    def make_room_name(self) -> str:
        return "yjs-" + str(self.scope["url_route"]["kwargs"]["pk"])

    async def make_ydoc(self) -> pycrdt.Doc:
        obj: TestDoc = await aget_object_or_404(TestDoc, pk=self.scope["url_route"]["kwargs"]["pk"])
        doc = obj.yjs
        doc.observe(self._doc_transaction)
        return doc

    async def receive(self, *args, **kwargs):
        await super().receive(*args, **kwargs)
        # Can't send channel messages inside of the observer callback, since sending is async,
        # the callback is sync, and async_to_sync can't be used since its running in an async
        # thread. So buffer them up and send when we can.
        for ev in self.updates_to_send:
            await self.channel_layer.send("poc-yjs-save", ev)
        self.updates_to_send.clear()

    def _doc_transaction(self, ev: pycrdt.TransactionEvent):
        self.updates_to_send.append({
            "type": "doc_updated",
            "connection_id": self.connection_id,
            "doc_pk": self.scope["url_route"]["kwargs"]["pk"],
            "user_pk": self.scope["user"].pk,
            "update_bytes": ev.update,
        })

    async def disconnect(self, *args, **kwargs) -> None:
        self.channel_layer.send("poc-yjs-save", {
            "type": "doc_flush",
            "connection_id": self.connection_id,
        })
        super().disconnect(*args, **kwargs)



class DebouncedCallback:
    task_name: str | None
    task: asyncio.Task | None
    cb: Callable[[], Coroutine[Any, Any, None]]

    def __init__(
            self,
            cb: Callable[[], Coroutine[Any, Any, None]],
            *,
            task_name: str | None = None
        ):
        self.cb = cb
        self.task_name = task_name
        self.ended = False
        self.task = None

    async def _task(self, delay: float):
        await asyncio.sleep(delay)
        await self.cb()

    def trigger(self, delay: float):
        if self.task is not None:
            self.task.cancel()
        self.task = asyncio.create_task(self._task(delay), name=self.task_name)

    def stop(self):
        if self.task is not None:
            self.task.cancel()



SAVE_DEBOUNCE_TIME = 1.0 # seconds

class SaveState:
    connection_id: str
    user_pk: int
    doc_pk: int
    updates: list[bytes]
    channel_layer: BaseChannelLayer
    save_debounce_cb: DebouncedCallback

    def __init__(
            self,
            connection_id: str,
            user_pk: int,
            doc_pk: int,
            channel_layer: BaseChannelLayer,
        ) -> None:
        self.connection_id = connection_id
        self.user_pk = user_pk
        self.doc_pk = doc_pk
        self.updates = []
        self.channel_layer = channel_layer
        self.save_debounce_cb = DebouncedCallback(self._debounce_cb)

    async def _debounce_cb(self):
        await self.channel_layer.send("poc-yjs-save", {
            "type": "doc_flush",
            "connection_id": self.connection_id,
        })

    def update(self, update_bytes: bytes) -> None:
        self.updates.append(update_bytes)
        self.save_debounce_cb.trigger(SAVE_DEBOUNCE_TIME)

    async def flush(self) -> None:
        self.save_debounce_cb.stop()
        if not self.updates:
            return

        await self._flush_db_sync()
        self.updates.clear()

    @database_sync_to_async
    def _flush_db_sync(self) -> None:
        with transaction.atomic():
            model = TestDoc.objects.select_for_update().get(pk=self.doc_pk)
            model_doc = model.yjs
            for update in self.updates:
                model_doc.apply_update(update)
            model.save()

        # DEBUG
        user = User.objects.get(pk=self.user_pk)
        description = model_doc.get("description", type=pycrdt.Text)
        text = f"UPDATE {user}:\n"
        for item, attrs in description.diff():
            text += f"\t{item!s} ({attrs!r})\n"
        print(text, end="", flush=True)
        # ENDDEBUG



class PocSaverConsumer(AsyncConsumer):
    pending: dict[str, SaveState]
    def __init__(self) -> None:
        super().__init__()
        self.pending = {}

    async def doc_updated(self, message: dict) -> None:
        connection_id: str = message["connection_id"]
        logger.warning("DEBUG: doc_updated from %s / %s", connection_id, message["user_pk"])
        if connection_id not in self.pending:
            self.pending[connection_id] = SaveState(
                connection_id,
                message["user_pk"],
                message["doc_pk"],
                channel_layer=self.channel_layer,
            )
        self.pending[connection_id].update(message["update_bytes"])

    async def doc_flush(self, message: dict) -> None:
        connection_id: str = message["connection_id"]
        logger.warning("DEBUG: doc_flush from %s", connection_id)
        if connection_id not in self.pending:
            return
        await self.pending[connection_id].flush()
        del self.pending[connection_id]
