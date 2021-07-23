import unittest
import fsglue
from tests import setup_env  # noqa
from typing import Union


def calc_sum(obj) -> int:
    return obj.num1 + obj.num2


class TestModel(fsglue.BaseModel):
    COLLECTION_PATH = "test"
    COLLECTION_PATH_PARAMS = []

    name = fsglue.StringProperty(required=True)
    num1 = fsglue.IntegerProperty(required=True)
    num2 = fsglue.IntegerProperty(required=True)
    sum = fsglue.ComputedProperty[Union[int, float]](computer=calc_sum)


class TestComputedProperty(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        for t in TestModel.all():
            t.delete()

    def test_property(self):
        doc1 = TestModel.create()
        doc1.name = "doc1"
        doc1.num1 = 2
        doc1.num2 = 3
        self.assertEqual(doc1.sum, 5)
        doc1.num1 = 5
        self.assertEqual(doc1.sum, 8)
        doc1.sum = 10  # will ignored
        self.assertNotEqual(doc1.sum, 10)
        doc1.put()
        doc1 = TestModel.get_by_id(doc1.doc_id)
        self.assertIsNotNone(doc1)
        if doc1:
            self.assertEqual(doc1.sum, 8)
            doc1_dict = doc1.to_dict()
            self.assertEqual(doc1_dict.get("sum"), 8)
            doc1 = TestModel.where([["name", "==", "doc1"], ["sum", "==", 8]])[0]
            self.assertEqual(doc1.sum, 8)
