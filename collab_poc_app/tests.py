from django.test import TestCase
import pycrdt
from .models import TestDoc

class TestDocTestCase(TestCase):
    def setUp(self):
        self.obj = TestDoc.objects.create()

    def test_rich_text_edit(self):
        description = self.obj.description
        self.assertIsInstance(description, pycrdt.XmlFragment)

        description.children.append("hello, world!")
        self.obj.save()

        obj2 = TestDoc.objects.get(pk=self.obj.pk)
        self.assertEqual(str(obj2.description), "hello, world!")

    def test_title_update_through_field(self):
        self.assertIs(self.obj.yjs_doc, self.obj.yjs_doc)

        self.obj.name = "Test Doc"

        self.assertEqual(str(self.obj.yjs_doc.get("non_collab_fields", type=pycrdt.Map)["name"]), "Test Doc")
        self.assertEqual(self.obj.name, "Test Doc")
        self.assertEqual(self.obj.stored_name, "Test Doc")
        self.obj.save()

        self.assertEqual(TestDoc.objects.values("stored_name").get(pk=self.obj.pk)["stored_name"], "Test Doc")
        obj2 = TestDoc.objects.get(pk=self.obj.pk)
        self.assertEqual(str(obj2.yjs_doc.get("non_collab_fields", type=pycrdt.Map)["name"]), "Test Doc")
        self.assertEqual(obj2.name, "Test Doc")
        self.assertEqual(obj2.stored_name, "Test Doc")

        obj3 = TestDoc.objects.get(stored_name="Test Doc")
        self.assertEqual(obj3.pk, obj2.pk)
        self.assertEqual(str(obj3.yjs_doc.get("non_collab_fields", type=pycrdt.Map)["name"]), "Test Doc")
        self.assertEqual(obj3.name, "Test Doc")
        self.assertEqual(obj3.stored_name, "Test Doc")

    def test_title_update_through_doc(self):
        self.obj.yjs_doc.get("non_collab_fields", type=pycrdt.Map)["name"] = "Test Doc"

        self.assertEqual(str(self.obj.yjs_doc.get("non_collab_fields", type=pycrdt.Map)["name"]), "Test Doc")
        self.assertEqual(self.obj.name, "Test Doc")
        self.obj.save()

        self.assertEqual(TestDoc.objects.values("stored_name").get(pk=self.obj.pk)["stored_name"], "Test Doc")
        obj2 = TestDoc.objects.get(pk=self.obj.pk)
        self.assertEqual(str(obj2.yjs_doc.get("non_collab_fields", type=pycrdt.Map)["name"]), "Test Doc")
        self.assertEqual(obj2.name, "Test Doc")
        self.assertEqual(obj2.stored_name, "Test Doc")

        obj3 = TestDoc.objects.get(stored_name="Test Doc")
        self.assertEqual(obj3.pk, obj2.pk)
        self.assertEqual(str(obj3.yjs_doc.get("non_collab_fields", type=pycrdt.Map)["name"]), "Test Doc")
        self.assertEqual(obj3.name, "Test Doc")
        self.assertEqual(obj3.stored_name, "Test Doc")
