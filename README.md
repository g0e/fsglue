
# fsglue

Simple ORM for google cloud firestore inspired by [datastore client library ndb](https://googleapis.dev/python/python-ndb/latest/index.html) and used by [Bizglue](https://bizglue.net/)(Japanese Only).

## Installation

```sh
pip install fsglue
```

## Simple Usage

```python
import fsglue

class Fruit(fsglue.BaseModel):
    COLLECTION_PATH = "fruit"
    COLLECTION_PATH_PARAMS = []

    name = fsglue.StringProperty(required=True)
    price = fsglue.IntegerProperty(required=True)


## create
apple = Fruit.create()
apple.name = "apple"
apple.price = 100
apple.put()

# get
apple = Fruit.get_by_id(apple.doc_id)
apple = Fruit.where([["name", "==", "apple"]])[0]

# update
apple.price = 120
apple.put()

# delete
apple.delete()
```

## Client Initialization

### case1

Initialize from the environment.
No code will be needed.

### case2

Initialize by `firestore.Client`.
Following code will pass kwargs to `firestore.Client(**kwargs)`.

```python
fsglue.initialize(**kwargs)
```

### case3

Initialize by firebase_admin.

```python
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
cred = credentials.Certificate('path/to/serviceAccount.json')
firebase_admin.initialize_app(cred)
```

## Model Samples

```python
class User(fsglue.BaseModel):
    COLLECTION_PATH = "users"
    COLLECTION_PATH_PARAMS = []

    name = fsglue.StringProperty(required=True)
    created_at = fsglue.TimestampProperty(auto_now=True)
    updated_at = fsglue.TimestampProperty(auto_now_add=True)

    @classmethod
    def create_by_name(cls, name):
        return cls.create_by_dict({"name": name})


# JsonSchema Definition for JsonProperty
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
```

## Operation Samples

### Create

Using `.create()` and `.put()`

```python
john = User.create()
john.name = "john"
john.put()

room1 = Room.create()
room1.name = "test"
room1.owner = john.doc_id
room1.tags = ["test"]
room1.put()

message11 = Message.create(room1.doc_id)  # parent_id = room1.doc_id
message11.body = "hello fsglue!"
message11.put()
```

Using `.create_by_dict()`

```python
john = User.create_by_dict({"name": "john"})
room1 = Roomt.create_by_dict({"name": "test", "owner": john.doc_id, "tags": ["test"]})
message11 = Message.create_by_dict({"body": "hello fsglue!"}, room1.doc_id) # parent_id = room1.doc_d
```

Using custom method

```python
john = User.create_by_name("john")
room1 = Room.create_by_user(john, tags=["test"])
message11 = Room.post_message(john, "hello fsglue!")
```

### Get

Using `.get_by_id()`

```python
john = User.get_by_id("xxx")  # return None if not exists
room1 = Room.get_by_id("yyy")
message11 = Message.get_by_id("zzz", room1.doc_id)
```

Using `.get_by_ids()`

```python
john = User.get_by_ids(["xxx"])[0]
room1 = Room.get_by_ids(["yyy"])[0]
message11 = Message.get_by_ids(["zzz"], room1.doc_id)[0]
```

Using `.all()`

```python
users = User.all(limit=10)
rooms = Room.all(limit=10)
messages1 = Message.all(room1.doc_id, limit=10)  # get messages belong to room1
```

Using `.where()`

```python
john = User.where([["name", "==", "john"]])[0]
room1 = Room.where([["name", "==", "room1"]])[0]
messages11 = Message.where([["body", "==", "hello fsglue!"]])[0]
```

Using `.stream()`

```python
for user in User.stream():  # iterate all users
    print(user)
```

### Update

Using `.get_by_id()` and `.put()`

```python
john = User.get_by_id("xxx")
john.name = "john!"
john.put()
```

Using `.update_by_dict()`

```python
john = User.update_by_dict({"id": "xxx", "name": "john!"})  # values require DocumentId in "id" field
room1 = Room.update_by_dict({"id": "yyy", "name": "test1"})
message11 = Message.update_by_dict({"id": "zzz", "body": "hello fsglue!?"}, room1.doc_id)
```

### Delete

Using `.get_by_id()` and `.delete()`

```python
john = User.get_by_id("xxx")
john.delete()
```

Using `.get_by_id()` and `.delete_all()`

```python
room1 = Room.get_by_id("yyy")
room1.delete_all()  # delete_all() will delete room1 and messages belong to room1
```

### Generate JsonSchema

`Room.to_schema()` will generate following JsonSchema definition

```js
{
  "type": "object",
  "required": [
    "name",
    "owner"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "name": {
      "type": "string"
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "owner": {
      "type": "string"
    },
    "created_at": {
      "type": "number"
    },
    "updated_at": {
      "type": "number"
    }
  }
}
```

## Links

- [API Reference](https://g0e.github.io/fsglue/)
