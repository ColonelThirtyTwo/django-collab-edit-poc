from typing import Any, Optional
from django.urls import reverse
import pycrdt

from django.db import models

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


class TestDoc(models.Model):
    yjs: pycrdt.Doc = YDocField()

    # Note: all fields except `yjs` are copies of the data stored in `yjs` and should
    # not be modified directly.
    name = models.CharField(max_length=255)
    description = models.TextField()
    contents = models.TextField()

    def set_fields_from_doc(self):
        self.name = str(self.yjs.get("non_collab_fields", type=pycrdt.Map).get("name", ""))
        self.description = str(self.yjs.get("description", type=pycrdt.XmlFragment))
        self.contents = str(self.yjs.get("contents", type=pycrdt.XmlFragment))

    def ydoc_repr(self):
        text = ""
        for field in ["name"]:
            val = self.yjs.get("non_collab_fields",type=pycrdt.Map).get(field, None)
            text += f"{field}: {val!r}\n"
        for field in ["description", "contents"]:
            text += f"{field}:\n\tText:\n"
            text += "".join(
                f"\t\t{content} ({attrs!r})\n"
                for (content, attrs) in self.yjs.get(field, type=pycrdt.Text).diff()
            )
            text += "\tXML: {}\n".format(self.yjs.get(field, type=pycrdt.XmlFragment))
        return text


    def get_absolute_url(self):
        return reverse("detail", kwargs={"pk": self.pk})
