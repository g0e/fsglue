import unittest
import fsglue
from tests import setup_env  # noqa


class YesNoProperty(fsglue.BaseProperty):
    # Return 'Yes' or 'No' for application and store True or False in firestore

    def to_app_value(self, value, obj):
        return "Yes" if bool(value) else "No"

    def from_app_value(self, value, obj):
        return True if value == "Yes" else False

    def to_db_value(self, value, obj):
        return bool(value)

    def from_db_value(self, value, obj):
        return bool(value)

    def get_schema(self):
        return {"type": "string", "enum": ["Yes", "No"]}


class TestModel(fsglue.BaseModel):
    COLLECTION_PATH = "test"
    COLLECTION_PATH_PARAMS = []

    name = fsglue.StringProperty(required=True)
    is_fine = YesNoProperty()


class TestYesNoProperty(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        for t in TestModel.all():
            t.delete()

    def test_property(self):
        john = TestModel.create_by_dict(
            {
                "name": "john",
                "is_fine": "No",
            }
        )
        self.assertEqual(john.is_fine, "No")
        john.is_fine = "Yes"
        self.assertEqual(john.is_fine, "Yes")
        john.is_fine = "N/A"  # will be "No"
        self.assertEqual(john.is_fine, "No")
        john.is_fine = "Yes"
        john.put()
        john = TestModel.get_by_id(john.doc_id)
        self.assertEqual(john.is_fine, "Yes")
        john_dict = john.to_dict()
        self.assertEqual(john_dict.get("is_fine"), "Yes")
        john = TestModel.where([["name", "==", "john"], ["is_fine", "==", "Yes"]])[0]
        self.assertEqual(john.is_fine, "Yes")
