from django.urls import reverse
import pycrdt

from pycrdt_model.models import YDocCopyField, YDocModelWithHistory


class TestDoc(YDocModelWithHistory):
    # Note: all fields except `yjs` are copies of the data stored in `yjs` and should
    # not be modified directly.
    name = YDocCopyField(["non_collab_fields", "name"], str, default="")

    RICH_TEXT_FIELDS = [
        ("description", "Description"),
        ("contents", "Contents"),
    ]

    @property
    def description(self) -> pycrdt.XmlFragment:
        return self.yjs_doc.get("description", type=pycrdt.XmlFragment)

    @property
    def contents(self) -> pycrdt.XmlFragment:
        return self.yjs_doc.get("contents", type=pycrdt.XmlFragment)

    def get_absolute_url(self):
        return reverse("detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

    def __repr__(self):
        return "TestDoc(name={!r}, description={!r}, contents={!r})".format(
            self.name,
            str(self.description),
            str(self.contents),
        )
