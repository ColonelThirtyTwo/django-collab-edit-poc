from typing import Any, Generic, Self, TypeVar
from django.db import models, transaction
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.core.exceptions import FieldDoesNotExist
from django.core import checks
import pycrdt._base


T = TypeVar("T")
V = TypeVar("V", bound=T)

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



# models.Field[pycrdt.Doc, pycrdt.Doc]
class YDocField(models.Field):
    """
    Django field for a yjs document.

    The document's client id will be set to zero.
    """
    # Based off of Django's BinaryField

    description = "YJS Document"
    empty_values = [None]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("editable", False)
        kwargs.setdefault("serialize", False)
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> Any:
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop("editable")
        kwargs.pop("serialize")
        return name, path, args, kwargs

    def get_internal_type(self) -> str:
        return "BinaryField"

    def from_db_value(
        self, value, _expression, _connection
    ):
        if value is None:
            return None
        doc = pycrdt.Doc(client_id=0)
        doc.apply_update(value)
        return doc

    def get_prep_value(self, value):
        if value is None:
            return None
        return value.get_update()

    def get_db_prep_value(self, value, connection, prepared=False):
        value = super().get_db_prep_value(value, connection, prepared)
        if value is not None:
            return connection.Database.Binary(value)
        return value

    def get_default(self):
        if self.has_default():
            if callable(self.default):
                return self.default()
            return self.default
        return pycrdt.Doc(client_id=0)



class YDocModel(models.Model):
    """
    Base class for models that contains a YDoc.

    Adds `yjs_doc` field, and copies `YField`s to their configured `copy_to_field` when saving.
    """

    class Meta:
        abstract = True

    yjs_doc: pycrdt.Doc = YDocField()

    def save(self, *args, **kwargs):
        for field in self._meta.concrete_fields:
            if isinstance(field, YField):
                field._do_copy_to_field(self)
        return super().save(*args, **kwargs)


class YDocModelWithHistory(YDocModel):
    """
    `YDocModel` that saves a `History` entry every time its saved.

    When `save`ing, if the doc has changed, this will also create a `History` entry containing the
    update from the state vector the model was loaded at to the state vector at time of saving. The
    history's `user` field can be provided as a keyword argument.
    """

    class Meta:
        abstract = True

    _state_vector_at_load: bytes | None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._state_vector_at_load = self.yjs_doc.get_state()

    def save(self, *args, user: User | int | None = None, **kwargs):
        """
        As Django's model save, but also saves a `History` entry for the update, if the doc changed.

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


def _resolve_path(doc: pycrdt.Doc, doc_value_path: str | list[str | int], typ: type[T], default: T | None = None) -> T | None:
    """
    Gets a possibly nested value from a YDoc via a path.

    If `doc_value_path` is a string, returns `doc.get(doc_value_path, type=typ)`.
    Otherwise `doc_value_path` must be a list whose first item is a string and remaining items strings or
    integers. This will traverse the document, indexing each element in the list order.
    """
    if isinstance(doc_value_path, str):
        return doc.get(doc_value_path, type=typ)

    if not doc_value_path:
        raise ValueError("Empty path")

    first = doc_value_path[0]
    if not isinstance(first, str):
        raise ValueError("doc_value_path must start with a string")

    if len(doc_value_path) == 1:
        return doc.get(first, type=typ)

    value: pycrdt.Map | pycrdt.Array = doc.get(
        first,
        type=pycrdt.Map if isinstance(doc_value_path[0], str) else pycrdt.Array,
    )
    for index in doc_value_path[1:]:
        try:
            value = value[index]
        except (KeyError, IndexError):
            return default
    return value


# models.Field[Never, T | None]
class YField(models.Field, Generic[T]):
    """
    Field that is a view into a YDoc value.

    Getting or setting this field will get or set the corresponding field in the ydoc.

    Copying
    -------

    The field may also optionally copy its value to another Django field, so that it can be
    accessed in queries, by setting `copy_to_field` to the field name to copy to. If the
    model is a subclass of `YDocModel`, fields will be copied on save, otherwise they are
    only copied when `YField` is assigned to.

    `Text` and `XmlFragment` items will be converted to text via the `str` function - this will
    lose information about embeds and formatting. Arrays and Maps are not yet supported.
    """

    def __init__(
        self,
        y_value_path: str | list[str | int],
        yjs_type: type[T] | None = None,
        *,
        copy_to_field: str | None = None,
        verbose_name: str | None = None,
        name: str | None = None,
        field: str = "yjs_doc",
    ):
        """
        Arguments:
        * `y_value_path`: Path to the item in the ydoc to get. If a string or one-element list, gets a top level element of the
          doc with type `yjs_type`. Otherwise, gets a value nested in a map or array by indexing with each list item in order.
        * `yjs_type`: If `y_value_path` is a string / one-item list, specifies the type to fetch from the top level document
          This should match the `type` argument to `Ydoc.get`. Must not be set for multi-element paths - maps and arrays have self
          describing types.
        * `copy_to_field`: If specified, copies this value to the named regular Django field. See class docs.
        * `field`: The name of the `YDocField` to get the value from. Defaults to `"yjs_doc"`, which is what `YDocModel` provides.
        """
        super().__init__(
            editable=False,
            null=True,
            blank=True,
            verbose_name=verbose_name,
            name=name,
        )
        self.y_value_path = y_value_path
        self.yjs_type = yjs_type
        self.ydoc_field = field
        self.copy_to_field = copy_to_field

    def check(self, **kwargs) -> list[checks.CheckMessage]:
        return [
            *self._check_field_name(),
            *self._check_yjs_doc_field(),
            *self._check_path(),
            *self._check_copy_to_field_field(),
        ]

    def _check_yjs_doc_field(self) -> list[checks.CheckMessage]:
        try:
            self.model._meta.get_field(self.ydoc_field)
        except FieldDoesNotExist:
            return [
                checks.Error(
                    "The YField object references the nonexistent field '%s'" % self.ydoc_field,
                    obj=self,
                    id="pycrdt_model.E001"
                )
            ]
        else:
            return []

    def _check_path(self) -> list[checks.CheckMessage]:
        if isinstance(self.y_value_path, str):
            return []
        if len(self.y_value_path) <= 0:
            return [
                checks.Error(
                    "The YField path is empty",
                    obj=self,
                    id="pycrdt_model.E002"
                )
            ]
        if not isinstance(self.y_value_path[0], str):
            return [
                checks.Error(
                    "The first element of the YField path must be a string",
                    obj=self,
                    id="pycrdt_model.E003"
                )
            ]
        return []
    
    def _check_yjs_type(self) -> list[checks.CheckMessage]:
        if isinstance(self.y_value_path, str) or len(self.y_value_path) == 1:
            if self.yjs_type is None:
                return [
                    checks.Error(
                        "The YField specifies a top level path but does not provide a type",
                        obj=self,
                        id="pycrdt_model.E004",
                    )
                ]
        elif self.yjs_type is not None:
            return [
                checks.Error(
                    "The YField provides a type but does not specify a top level path",
                    obj=self,
                    id="pycrdt_model.E005",
                )
            ]
        return []

    def _check_copy_to_field_field(self) -> list[checks.CheckMessage]:
        if self.copy_to_field is None:
            return []
        try:
            self.model._meta.get_field(self.copy_to_field)
        except FieldDoesNotExist:
            return [
                checks.Error(
                    "The YField copy_to_field reference the nonexistent field '%s'." % self.copy_to_field,
                    obj=self,
                    id="pycrdt_model.E004",
                )
            ]
        return []

    def _get_from_model(self, instance: models.Model) -> T | None:
        doc = getattr(instance, self.ydoc_field)
        return _resolve_path(doc, self.y_value_path, self.yjs_type)

    def _do_copy_to_field(self, instance: models.Model):
        if self.copy_to_field is None:
            return
        setattr(instance, self.copy_to_field, _yjs_to_db(self._get_from_model(instance)))

    def get_attname_column(self):
        attname, column = super().get_attname_column()
        return attname, None

    def contribute_to_class(self, cls, name, **kwargs) -> None:
        super().contribute_to_class(cls, name, **kwargs)
        setattr(cls, self.attname, YFieldDescriptor(self))

    def deconstruct(self):
        name, path, _, kwargs = super().deconstruct()
        kwargs.pop("editable")
        kwargs.pop("null")
        kwargs.pop("blank")
        if self.copy_to_field is not None:
            kwargs["copy_to_field"] = self.copy_to_field
        args = (self.y_value_path,)
        if self.yjs_type is not None:
            args += (self.yjs_type,)
        return name, path, args, kwargs

    def get_default(self) -> Any:
        if not self.has_default():
            # Many Django functions will 
            # Return a marker object that `YFieldDescriptor.__set__` knows about and ignores
            return _YFIELD_DEFAULT
        return super().get_default()



class YFieldDescriptor(Generic[T]):
    """
    Descriptor used with YField, getting the 
    """
    def __init__(self, field: YField[T]):
        self.field = field

    def __get__(self, instance: models.Model | None, cls: Any = None) -> T | None:
        if instance is None:
            return self
        return self.field._get_from_model(instance)

    def __set__(self, instance: models.Model | None, value: V) -> V:
        if value is _YFIELD_DEFAULT:
            return value
        if isinstance(value, pycrdt._base.BaseType):
            raise RuntimeError("Cannot set a Pycrdt type directly, go through the doc instead")
        
        doc = getattr(instance, self.field.ydoc_field)
        if isinstance(self.field.y_value_path, str):
            doc[self.field.y_value_path] = value
        elif len(self.field.y_value_path) == 1:
            doc[self.field.y_value_path[0]] = value
        else:
            base = _resolve_path(
                doc,
                self.field.y_value_path[:-1],
                pycrdt.Map if isinstance(self.field.y_value_path[-1], str) else pycrdt.Array,
                None
            )
            base[self.field.y_value_path[-1]] = value

        if self.field.copy_to_field is not None:
            setattr(instance, self.field.copy_to_field, _yjs_to_db(value))

        return value


def _yjs_to_db(value: Any) -> Any:
    """
    Helper: converts a value from a YDoc to a value for a Django field.
    """
    if isinstance(value, pycrdt.XmlFragment) or isinstance(value, pycrdt.Text):
        return str(value)
    return value

_YFIELD_DEFAULT = object()
