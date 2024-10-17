from typing import Any, Optional, Self
from django.db import models, transaction
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from computedfields.models import (
    ComputedField,
    ComputedFieldsModel,
    ComputedFieldsAdminModel,
)
import pycrdt


class History(models.Model):
    """
    Change of a `YDocModelWithHistory`.
    """

    id = models.BigAutoField(primary_key=True)
    target_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target_id = models.PositiveIntegerField()
    target = GenericForeignKey("target_type", "target_id")
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    time = models.DateTimeField(auto_now_add=True)
    update = models.BinaryField()

    class Meta:
        indexes = [
            models.Index(fields=["target_type", "target_id", "id"]),
        ]

    @classmethod
    def for_object(cls, obj: "YDocModelWithHistory", recent_first: bool = False):
        """
        Gets a `QuerySet` of history entries for an object.

        The history is ordered from first to last, unless `recent_first` is set which will
        reverse the order.

        It's recommended to bound time based on the `id` field since its monotonically increasing and
        has no conflicts.
        """
        return cls.objects.filter(
            target_type=ContentType.objects.get_for_model(obj),
            target_id=obj.pk,
        ).order_by("-id" if recent_first else "id")

    @classmethod
    def replay(
        cls, obj: "YDocModelWithHistory", until_id: int, until_id_inclusive: bool = True
    ) -> pycrdt.Doc:
        """
        Gets a `pycrdt.Doc` with the state at the time of the last update at or until `until_id`.
        """
        doc = pycrdt.Doc()
        with doc.transaction():
            qs = cls.for_object(obj)
            if until_id_inclusive:
                qs = qs.filter(id__lte=until_id)
            else:
                qs = qs.filter(id__lt=until_id)
            for history_entry in qs:
                doc.apply_update(history_entry.update)
        return doc

    @classmethod
    def replay_until(
        cls, obj: "YDocModelWithHistory", history_id: int
    ) -> tuple[pycrdt.Doc, Self] | None:
        """
        Gets the history entry with the specified ID and also the doc as it appeared up to that point, excluding the specified update.

        That is, the returned doc will be the state of the doc before the `history_id` update.

        You can add observers to the returend document then apply the returned `History.update`, and the observers will be called
        with the changes introduced in this history instance.

        If there is no `History` with the passed in `history_id`, returns None.
        """
        doc = pycrdt.Doc()
        last_entry = None
        with doc.transaction():
            for history_entry in cls.for_object(obj).filter(id__lte=history_id):
                if last_entry is not None:
                    doc.apply_update(last_entry.update)
                last_entry = history_entry
        if last_entry is None or last_entry.id != history_id:
            return None
        return (doc, last_entry)


class YDocField(models.BinaryField):
    """
    Django field for a yjs document.

    The document's client id will be set to zero.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_default(self) -> pycrdt.Doc:
        return pycrdt.Doc(client_id=0)

    def from_db_value(self, value, _expression, _connection):
        if value is None:
            return None
        doc = pycrdt.Doc(client_id=0)
        doc.apply_update(value)
        return doc

    def get_prep_value(self, value: Optional[pycrdt.Doc]) -> Optional[bytes]:
        if value is None:
            return None
        return value.get_update()


class YDocModel(ComputedFieldsModel):
    """
    Base class for models that contains a YDoc.

    Adds `yjs_doc` field and sets up for `YDocCopyField` to work.
    """

    class Meta:
        abstract = True

    yjs_doc: pycrdt.Doc = YDocField()


class YDocModelWithHistory(YDocModel):
    """
    `YDocModel` that saves a `History` entry every time its saved.

    `save` also creates a `History` entry containing the update from the state vector the model was
    loaded at to the state vector at time of saving. The history's `user` field can be provided as
    a keyword argument.
    """

    class Meta:
        abstract = True

    _state_vector_at_load: bytes | None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._state_vector_at_load = self.yjs_doc.get_state()

    def save(self, *args, user: User | int = None, **kwargs):
        """
        As Django's model save, but also saves a `History` entry for the update.

        If `user` is provided (either its ID or the model itself), `History.author` will be set to the provided user.
        """
        if self._state_vector_at_load == self.yjs_doc.get_state():
            # No actual changes with the doc, don't save a new history entry
            return super().save(*args, **kwargs)

        update = self.yjs_doc.get_update(self._state_vector_at_load)
        with transaction.atomic():
            super().save(*args, **kwargs)
            history = History(target=self, update=update)
            if isinstance(user, int):
                history.author_id = user
            else:
                history.author = user
            history.save()


def _resolve_path(doc: pycrdt.Doc, doc_value_path: str | list[str | int], typ: type):
    """
    Gets a possibly nested value from a YDoc via a path.

    If `doc_value_path` is a string, returns `doc.get(doc_value_path, type=typ)`.
    Otherwise `doc_value_path` must be a list whose first item is a string and remaining items strings or
    integers. This will traverse the document, indexing each element in the list order.
    """
    if isinstance(doc_value_path, str):
        return doc.get(doc_value_path, typ)
    if not doc_value_path:
        raise ValueError("Empty path")
    if len(doc_value_path) == 1:
        return doc.get(doc_value_path[0], typ)
    value = doc.get(
        doc_value_path[0],
        type=pycrdt.Map if isinstance(doc_value_path[1], str) else pycrdt.Array,
    )
    for index in doc_value_path[1:]:
        value = value[index]
    return value


# Underlying field types for YDocCopyField
_DOC_TYPE_TO_FIELD = {
    pycrdt.XmlFragment: models.TextField,
    pycrdt.Text: models.TextField,
    str: models.TextField,
    int: models.IntegerField,
    float: models.FloatField,
    bool: models.BooleanField,
    bytes: models.BinaryField,
}


def YDocCopyField(
    doc_value_path: str | list[str | int],
    doc_value_typ: type,
    *,
    null: bool = False,
    default: Any | None = None,
):
    """
    Field that is a view/copy of a field in the YDoc.

    Use this if you want to refer to a field in a YDoc in a query or index.
    """
    if doc_value_typ not in _DOC_TYPE_TO_FIELD:
        raise ValueError("Type not implement for YDocCopyField: " + repr(doc_value_typ))

    def do_compute(this):
        try:
            value = _resolve_path(this.yjs_doc, doc_value_path, doc_value_typ)
        except KeyError:
            return default
        except IndexError:
            return default
        if isinstance(value, pycrdt.XmlFragment) or isinstance(value, pycrdt.Text):
            return str(value)
        return value

    return ComputedField(
        _DOC_TYPE_TO_FIELD[doc_value_typ](null=null),
        depends=[("self", ["yjs_doc"])],
        compute=do_compute,
    )
