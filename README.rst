
fsglue
=====================


Simple ORM for google cloud firestore inspired by ndb.

Installation
---------------------

.. code-block:: sh

    pip install fsglue


Usage
---------------------

.. code-block:: python

    import fsglue

    class Person(fsglue.BaseModel):
        COLLECTION_PATH = "group/{0}/person"
        COLLECTION_PATH_PARAMS = ["group_id"]

        name = fsglue.StringProperty(required=True)
        age = fsglue.IntegerProperty(required=True)

