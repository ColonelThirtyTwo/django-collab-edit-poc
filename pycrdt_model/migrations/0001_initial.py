# Generated by Django 5.1.2 on 2024-10-09 17:34

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="History",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("target_id", models.PositiveIntegerField()),
                ("time", models.DateTimeField(auto_now_add=True)),
                ("update", models.BinaryField()),
                (
                    "author",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "target_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["target_type", "target_id", "id"],
                        name="pycrdt_mode_target__f1c58a_idx",
                    )
                ],
            },
        ),
    ]
