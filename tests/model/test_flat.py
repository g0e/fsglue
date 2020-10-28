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

    def test_where(self):
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
        fruits = Fruit.all()
        self.assertEqual(len(fruits), 3)
        fruits = Fruit.where([["name", "==", "apple"]])
        self.assertEqual(len(fruits), 1)
        self.assertEqual(apple.doc_id, fruits[0].doc_id)
        fruits = Fruit.where([], order_by="price", limit=2)
        self.assertEqual(len(fruits), 2)
        self.assertEqual(fruits[0].doc_id, orange.doc_id)
        self.assertEqual(fruits[1].doc_id, apple.doc_id)
        fruits = Fruit.where([], order_by="-price")
        self.assertEqual(len(fruits), 3)
        self.assertEqual(fruits[0].doc_id, banana.doc_id)

    def test_create_and_update_by_instance(self):
        fruit = Fruit.create()
        fruit.name = "apple"
        fruit.price = 123
        fruit.put()
        self.assertNotEqual(fruit.doc_id, None)
        apple = Fruit.get_by_id(fruit.doc_id)
        self.assertEqual("apple", apple.name)
        self.assertEqual(123, apple.price)
        fruit.name = "nice apple"
        fruit.price = 234
        fruit.put()
        nice_apple = Fruit.get_by_id(fruit.doc_id)
        self.assertEqual("nice apple", nice_apple.name)
        self.assertEqual(234, nice_apple.price)
        self.assertEqual(fruit.doc_id, nice_apple.doc_id)

    def test_get_by_ids(self):
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
        fruits = Fruit.get_by_ids([apple.doc_id, banana.doc_id])
        self.assertEqual(len([f for f in fruits if f.name == "apple"]), 1)
        self.assertEqual(len([f for f in fruits if f.name == "banana"]), 1)
