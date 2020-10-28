import unittest
import fsglue
from tests import setup_env  # noqa


ITEMS_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "items": {
        "type": "object",
        "required": ["name", "price", "cnt"],
        "additionalProperties": False,
        "properties": {
            "name": {
                "type": "string",
            },
            "price": {
                "type": "number",
            },
            "cnt": {
                "type": "number",
            },
        },
    },
}

COUPON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["coupon_id", "coupon_name", "condition"],
    "properties": {
        "coupon_id": {
            "type": "string",
        },
        "coupon_name": {
            "type": "string",
        },
        "condition": {"type": "object", "additionalProperties": True},
    },
}


class Purchase(fsglue.BaseModel):
    COLLECTION_PATH = "purchase"
    COLLECTION_PATH_PARAMS = []

    items = fsglue.JsonProperty(schema=ITEMS_SCHEMA, default=[], required=True)
    coupon = fsglue.JsonProperty(schema=COUPON_SCHEMA, default=None)


class TestJsonProperty(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        for t in Purchase.all():
            t.delete()

    def test_property(self):
        purchase = Purchase.create()
        with self.assertRaises(fsglue.FsglueValidationError):
            purchase.items = []  # minItems: 1
        purchase.items = [{"name": "apple", "price": 100, "cnt": 1}]
        purchase.put()
        self.assertEqual(len(purchase.items), 1)
        self.assertEqual(purchase.coupon, None)
        purchase = Purchase.get_by_id(purchase.doc_id)
        with self.assertRaises(fsglue.FsglueValidationError):
            purchase.coupon = {
                "coupon_id": "test",
                "coupon_name": "time sale 10% off",
                # require condition
            }
        purchase.coupon = {
            "coupon_id": "test",
            "coupon_name": "time sale 10% off",
            "condition": {"discount_rate": 0.9},
        }
        purchase.put()
