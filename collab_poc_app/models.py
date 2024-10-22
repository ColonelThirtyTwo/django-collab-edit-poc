from django.db import models
from django.urls import reverse
import pycrdt

from pycrdt_model.models import YField, YDocModelWithHistory


class TestDoc(YDocModelWithHistory):
    stored_name = models.TextField("name", null=True, blank=True, editable=False)
    name = YField(["non_collab_fields", "name"], copy_to_field="stored_name")
    stored_score = models.IntegerField("score", null=True, blank=True, editable=False)
    score = YField(["non_collab_fields", "score"], copy_to_field="stored_score")

    description = YField("description", pycrdt.XmlFragment)
    contents = YField("contents", pycrdt.XmlFragment)

    RICH_TEXT_FIELDS = [
        ("description", "Description"),
        ("contents", "Contents"),
    ]

    def get_absolute_url(self):
        return reverse("detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

    def __repr__(self):
        return "TestDoc(name={!r}, score={!r}, description={!r}, contents={!r})".format(
            self.name,
            self.score,
            str(self.description),
            str(self.contents),
        )
