import unittest
import fsglue
from tests import setup_env  # noqa


class Fruit(fsglue.BaseModel):
    COLLECTION_PATH = "fruit"
    COLLECTION_PATH_PARAMS = []

    name = fsglue.StringProperty(required=True)
    price = fsglue.IntegerProperty(required=True)


class TestFruit(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        for fruit in Fruit.all():
            fruit.delete()

    def test_crud(self):
        # create
        apple = Fruit.create_by_dict(
            {
                "name": "apple",
                "price": 100,
            }
        )
        self.assertEqual(apple.name, "apple")
        self.assertEqual(apple.price, 100)
        # read
        fetched_apple = Fruit.get_by_id(apple.doc_id)
        self.assertEqual(apple.doc_id, fetched_apple.doc_id)
        self.assertEqual(apple.name, "apple")
        self.assertEqual(apple.price, 100)
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

    def test_list_fetch(self):
        apple = Fruit.create_by_dict(
            {
                "name": "apple",
                "price": 100,
            }
        )
        banana = Fruit.create_by_dict(
            {
                "name": "banana",
                "price": 200,
            }
        )
        orange = Fruit.create_by_dict(
            {
                "name": "orange",
                "price": 60,
            }
        )
        Fruit.all()