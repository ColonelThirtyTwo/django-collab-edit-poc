# Generated by Django 5.1.2 on 2024-10-22 19:20

import pycrdt._xml
import pycrdt_model.models
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TestDoc",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("yjs_doc", pycrdt_model.models.YDocField()),
                (
                    "stored_name",
                    models.TextField(
                        blank=True, editable=False, null=True, verbose_name="name"
                    ),
                ),
                (
                    "name",
                    pycrdt_model.models.YField(
                        ["non_collab_fields", "name"], copy_to_field="stored_name"
                    ),
                ),
                (
                    "stored_score",
                    models.IntegerField(
                        blank=True, editable=False, null=True, verbose_name="score"
                    ),
                ),
                (
                    "score",
                    pycrdt_model.models.YField(
                        ["non_collab_fields", "score"], copy_to_field="stored_score"
                    ),
                ),
                (
                    "description",
                    pycrdt_model.models.YField("description", pycrdt._xml.XmlFragment),
                ),
                (
                    "contents",
                    pycrdt_model.models.YField("contents", pycrdt._xml.XmlFragment),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
