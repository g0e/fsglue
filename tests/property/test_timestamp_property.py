import unittest
import fsglue
from tests import setup_env  # noqa
import datetime


class TestModel(fsglue.BaseModel):
    COLLECTION_PATH = "test"
    COLLECTION_PATH_PARAMS = []

    name = fsglue.StringProperty(required=True)
    born_at = fsglue.TimestampProperty()
    created_at = fsglue.TimestampProperty(auto_now_add=True)
    updated_at = fsglue.TimestampProperty(auto_now=True)


class TestTimestampProperty(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        for t in TestModel.all():
            t.delete()

    def test_property(self):
        start_at = datetime.datetime.now().timestamp()
        john = TestModel.create()
        john.name = "john"
        john.born_at = start_at
        self.assertEqual(john.born_at, start_at)
        self.assertEqual(john.created_at, None)
        self.assertEqual(john.updated_at, None)
        john.put()
        john = TestModel.get_by_id(john.doc_id)
        self.assertIsNotNone(john)
        if john:
            self.assertEqual(john.born_at, start_at)
            self.assertGreaterEqual(john.created_at, start_at)
            self.assertLessEqual(john.created_at, datetime.datetime.now().timestamp())
            self.assertGreaterEqual(john.updated_at, start_at)
            self.assertLessEqual(john.updated_at, datetime.datetime.now().timestamp())
            updated_at = datetime.datetime.now().timestamp()
            john.put()
            # assert should and should not update
            john2 = TestModel.get_by_id(john.doc_id)
            self.assertIsNotNone(john2)
            if john2:
                self.assertEqual(john2.born_at, start_at)
                self.assertEqual(john2.created_at, john.created_at)
                self.assertGreaterEqual(john2.updated_at, updated_at)
                self.assertLessEqual(john2.updated_at, datetime.datetime.now().timestamp())
                # assert can and cannot update
                tmp_value = datetime.datetime.now().timestamp()
                john2.born_at = tmp_value
                john2.updated_at = tmp_value
                john2.created_at = tmp_value
                self.assertEqual(john2.born_at, tmp_value)
                self.assertNotEqual(john2.updated_at, tmp_value)
                self.assertNotEqual(john2.created_at, tmp_value)
