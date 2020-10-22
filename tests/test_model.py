import unittest
import fsglue
from tests import setup_env  # noqa


class Fruit(fsglue.BaseModel):
    COLLECTION_PATH = "fruit"
    COLLECTION_PATH_PARAMS = []

    name = fsglue.StringProperty(required=True)
    price = fsglue.IntegerProperty(required=True)


class TestFruit(unittest.TestCase):

    def test_crud(self):
        # create
        new_apple = Fruit.create_by_dict({
            "name": "apple",
            "price": 100,
        })
        self.assertEqual(new_apple.name, "apple")
        self.assertEqual(new_apple.price, 100)
        # read
        fetched_apple = Fruit.get_by_id(new_apple.doc_id)
        self.assertEqual(new_apple.doc_id, fetched_apple.doc_id)
        self.assertEqual(new_apple.name, "apple")
        self.assertEqual(new_apple.price, 100)
        # update
        values = fetched_apple.to_dict()
        values["price"] = 110
        Fruit.update_by_dict(values)
        fetched_apple = Fruit.get_by_id(fetched_apple.doc_id)
        self.assertEqual(fetched_apple.name, "apple")
        self.assertEqual(fetched_apple.price, 110)
        # delete
        fetched_apple.delete()
        self.assertEqual(Fruit.exists(fetched_apple.doc_id), False)
