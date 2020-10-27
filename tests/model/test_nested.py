import unittest
import fsglue
from tests import setup_env  # noqa


class User(fsglue.BaseModel):
    COLLECTION_PATH = "users"
    COLLECTION_PATH_PARAMS = []

    name = fsglue.StringProperty(required=True)
    created_at = fsglue.TimestampProperty(auto_now=True)
    updated_at = fsglue.TimestampProperty(auto_now_add=True)

    @classmethod
    def create_by_name(cls, name):
        return cls.create_by_dict({"name": name})


TAGS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "string",
    },
}


class Room(fsglue.BaseModel):
    COLLECTION_PATH = "rooms"
    COLLECTION_PATH_PARAMS = []

    name = fsglue.StringProperty(required=True)
    owner = fsglue.StringProperty(required=True)
    tags = fsglue.JsonProperty(schema=TAGS_SCHEMA, default=[])
    created_at = fsglue.TimestampProperty(auto_now=True)
    updated_at = fsglue.TimestampProperty(auto_now_add=True)

    @classmethod
    def create_by_user(cls, user, tags=[]):
        room = cls.create()
        room.name = "untitled"
        room.owner = user.doc_id
        room.tags = tags
        room.put()
        return room

    def post_message(self, user, body):
        msg = Message.create(self.doc_id)
        msg.body = body
        msg.created_by = user.doc_id
        msg.put()
        return msg

    def fetch_latest_messages(self):
        return Message.all(self.doc_id, limit=100, order_by="-created_at")


class Message(fsglue.BaseModel):
    COLLECTION_PATH = "rooms/{0}/messages"
    COLLECTION_PATH_PARAMS = ["room_id"]

    body = fsglue.StringProperty(required=True)
    created_by = fsglue.StringProperty(required=True)
    created_at = fsglue.TimestampProperty(auto_now=True)


class TestFruit(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        for user in User.all():
            user.delete()
        for room in Room.all():
            room.delete_all()

    def test_models(self):
        # users
        john = User.create_by_name("john")
        joe = User.create_by_name("joe")
        jane = User.create_by_name("jane")
        # rooms
        room1 = Room.create_by_user(john)
        self.assertEqual(room1.tags, [])
        room2 = Room.create_by_user(john, ["test"])
        self.assertEqual(room2.tags, ["test"])
        # message for room1
        room1.post_message(john, "hello!!")
        room1.post_message(joe, "hello!?")
        room1.post_message(joe, "goodbye!!")
        room1.post_message(john, "goodbye!?")
        # message for room2
        room2.post_message(john, "1 + 2 = ?")
        room2.post_message(jane, "3")
        # assert messages
        room1_messages = room1.fetch_latest_messages()
        self.assertEqual(len(room1_messages), 4)
        self.assertEqual(room1_messages[0].body, "goodbye!?")
        self.assertEqual(room1_messages[1].body, "goodbye!!")
        room2_messages = room2.fetch_latest_messages()
        self.assertEqual(len(room2_messages), 2)
        self.assertEqual(room2_messages[0].body, "3")
