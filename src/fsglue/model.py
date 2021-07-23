# inspired by https://github.com/GoogleCloudPlatform/datastore-ndb-python/blob/master/ndb/model.py
from .client import get_client
from .exceptions import FsglueValidationError, FsglueDocumentNotFound
import re
from .property import BaseProperty
from typing import TypeVar, Any, Optional, Type


class MetaModel(type):
    def __init__(cls, name, bases, classdict):
        super(MetaModel, cls).__init__(name, bases, classdict)
        cls._fix_up_properties()  # type: ignore


T = TypeVar('T')
Model = TypeVar('Model', bound='BaseModel')


class BaseModel(object, metaclass=MetaModel):
    """BaseModel


    Examples:
        .. code-block:: python

            import fsglue

            class Fruit(fsglue.BaseModel):

                COLLECTION_PATH = "fruit"
                COLLECTION_PATH_PARAMS = []

                name = fsglue.StringProperty(required=True)
                price = fsglue.IntegerProperty(required=True)

            # create
            apple = Fruit.create_by_dict({"name": "apple", "price": 100})

            # read
            apple = Fruit.get_by_id(apple.doc_id)
            apple = Fruit.where([[name, "==", "apple"]])[0]

            # update
            values = fetched_apple.to_dict()
            values["price"] = 110
            Fruit.update_by_dict(values)
            fetched_apple = Fruit.get_by_id(fetched_apple.doc_id)
            # delete
            fetched_apple.delete()

    """

    COLLECTION_PATH: str = None  # type: ignore # ex: category/{0}/group/{1}/page
    COLLECTION_PATH_PARAMS: list[str] = []  # ex: ["category_id", "group_id"]
    DICT_ID_KEY: str = "id"
    ID_VALIDATION_PATTERN = r"^[a-zA-Z0-9_]+$"
    _properties: dict[str, BaseProperty] = {}

    @classmethod
    def _fix_up_properties(cls):
        cls._properties = {}
        for name in cls.__dict__.keys():
            prop = getattr(cls, name, None)
            if isinstance(prop, BaseProperty):
                prop._fix_up(cls, name)
                if prop._name is not None:
                    cls._properties[prop._name] = prop

    def __init__(self, doc_id, *parent_ids):
        self._doc_id = doc_id
        self._doc_values = {}
        self._parent_ids = parent_ids
        for name, value in zip(self.COLLECTION_PATH_PARAMS, parent_ids):
            setattr(self, "_" + name, value)

    def _get_col_path(self):
        return self.COLLECTION_PATH.format(*self._parent_ids)

    @classmethod
    def _get_col_path_by_ids(cls, *parent_ids):
        return cls.COLLECTION_PATH.format(*parent_ids)

    @classmethod
    def get_client(cls):
        """Return firestore.Clinet() instance. You can override this method to use another client per model."""
        return get_client()

    @property
    def doc_id(self) -> Optional[str]:
        return self._doc_id

    def to_dict(self, get_intact=False) -> dict[str, Any]:
        """Return dict values of instance propeties

        Args:
            get_intact (bool): if True return values before local change
        Returns:
            dict: document values
        """
        values = {}
        for k in self._properties.keys():
            prop = self._properties[k]
            values[k] = prop._get_app_value(self, get_intact=get_intact)
        values[self.DICT_ID_KEY] = self._doc_id
        return values

    def _to_db_dict(self, exclude=[], only=None):
        "Generate dict for firestore"
        values = {}
        for k in self._properties.keys():
            if only and k not in only:
                continue
            if k in exclude:
                continue
            prop = self._properties[k]
            if prop.is_virtual:
                continue
            values[k] = prop._get_db_value(self)
        return values

    def _from_dict(self, values={}):
        """Update instance values by dict

        Args:
            values (dict): new values
        """
        for k in self._properties.keys():
            if k in values:
                self._properties[k]._set_app_value(self, values[k])

    def _from_db_dict(self, values={}):
        """Update instance values by firestore values"""
        for k in self._properties.keys():
            prop = self._properties[k]
            if prop.is_virtual:
                continue
            if k in values:
                prop._set_db_value(self, values[k])

    @classmethod
    def create(cls, *parent_ids):
        """Create new model instance

        Args:
            *parent_ids (list[str]): List of parent_id defined by :attr:`COLLECTION_PATH_PARAMS`

        Returns:
            obj: model instance
        """
        return cls(None, *parent_ids)

    @classmethod
    def create_by_dict(
        cls, values, *parent_ids, exclude=[], only=None, without_put=False
    ):
        """Create new firestore document by dict values, and return model instance.

        Args:
            values (dict): Model properties values.
            *parent_ids (list[str]): List of parent_id defined by :attr:`COLLECTION_PATH_PARAMS`
            exclude (list[str], optional): If specified, save property not listed.
            only (list[str], optional): If specified, save property only listed.
            without_put (bool): If True, do not save on firestore but create instance.

        Returns:
            obj: model instance
        """
        doc_id = values.get(cls.DICT_ID_KEY)
        if doc_id:
            cls._validate_doc_id(doc_id)
        doc_values = cls._filter_values(values, exclude=exclude, only=only)
        obj = cls(doc_id, *parent_ids)
        obj._from_dict(doc_values)
        if not without_put:
            obj.put()
        else:
            obj._validate()
            obj.validate()
        return obj

    @classmethod
    def _validate_doc_id(cls, doc_id):
        if cls.ID_VALIDATION_PATTERN:
            if not re.match(cls.ID_VALIDATION_PATTERN, doc_id):
                raise FsglueValidationError("invalid id: {0}".format(doc_id))

    @classmethod
    def update_by_dict(
        cls, values, *parent_ids, exclude=[], only=None, without_put=False
    ):
        """Update firestore document by dict values, and return model instance.

        Args:
            values (dict): Model properties values. Must contain :attr:`DICT_ID_KEY` field.
            *parent_ids (list[str]): List of parent_id defined by :attr:`COLLECTION_PATH_PARAMS`
            exclude (list[str], optional): If specified, save property not listed.
            only (list[str], optional): If specified, save property only listed.
            without_put (bool): If True, do not save on firestore but update instance.

        Returns:
            obj: model instance
        """
        doc_id = values.get(cls.DICT_ID_KEY)
        if not doc_id:
            raise FsglueValidationError(cls.DICT_ID_KEY + " not found")
        new_values = cls._filter_values(values, exclude=exclude, only=only)
        obj = cls.get_by_id(doc_id, *parent_ids)
        if not obj:
            raise FsglueDocumentNotFound()
        obj._from_dict(new_values)
        if not without_put:
            obj.put(exclude=exclude, only=only)
        else:
            obj._validate()
            obj.validate()
        return obj

    @classmethod
    def upsert_by_dict(
        cls, values, *parent_ids, exclude=[], only=None, without_put=False
    ):
        """Create or update firestore document by dict values, and return model instance.

        Args:
            values (dict): Model properties values. Must contain :attr:`DICT_ID_KEY` field.
            *parent_ids (list[str]): List of parent_id defined by :attr:`COLLECTION_PATH_PARAMS`
            exclude (list[str], optional): If specified, save property not listed.
            only (list[str], optional): If specified, save property only listed.
            without_put (bool): If True, do not save on firestore.

        Returns:
            obj: model instance
        """
        doc_id = values.get(cls.DICT_ID_KEY)
        if not doc_id:
            raise FsglueValidationError(cls.DICT_ID_KEY + " not found")
        if cls.exists(doc_id, *parent_ids):
            return cls.update_by_dict(
                values, *parent_ids, exclude=exclude, only=only, without_put=without_put
            )
        else:
            return cls.create_by_dict(
                values, *parent_ids, exclude=exclude, only=only, without_put=without_put
            )

    @classmethod
    def _filter_values(cls, values, exclude=[], only=None):
        new_values = {}
        if only:
            for key in only:
                new_values[key] = values.get(key)
        else:
            for key in values.keys():
                if key not in exclude:
                    new_values[key] = values.get(key)
        return new_values

    @classmethod
    def _parent_ids_from_path(cls, path):
        # extract parent_ids from path (used in collection_group feature)
        parent_ids = []
        for key, value in zip(cls.COLLECTION_PATH.split("/"), path.split("/")):
            if key.startswith("{") and key.endswith("}"):
                parent_ids.append(value)
        return parent_ids

    def _validate(self):
        """Do validate by _properties._validate"""
        for k in self._properties.keys():
            prop = self._properties[k]
            if hasattr(prop, "_get_validate_value"):
                value = prop._get_validate_value(self)  # type: ignore
            else:
                value = prop._get_app_value(self)
            prop._validate(value, self)

    def validate(self):
        """Validate model instance. Raise Exception if invalid"""
        pass

    @classmethod
    def exists(cls, doc_id, *parent_ids) -> bool:
        """Return the document exists or not by doc_id.

        Args:
            doc_id (str): Document id
            *parent_ids (list[str]): List of parent_id defined by :attr:`COLLECTION_PATH_PARAMS`
        Returns:
            bool: True if exists else False
        """
        return (
            cls.get_client()
            .collection(cls._get_col_path_by_ids(*parent_ids))
            .document(doc_id)
            .get()
            .exists
        )

    @classmethod
    def get_by_id(cls, doc_id, *parent_ids):
        """Fetch document from firestore by doc_id

        Args:
            doc_id (str): Document id
            *parent_ids (list[str]): List of parent_id defined by :attr:`COLLECTION_PATH_PARAMS`
        Returns:
            obj: model instance
        """
        doc = (
            cls.get_client()
            .collection(cls._get_col_path_by_ids(*parent_ids))
            .document(doc_id)
            .get()
        )
        if doc.exists:
            obj = cls(doc.id, *parent_ids)
            obj._from_db_dict(doc.to_dict())
            return obj
        return None

    @classmethod
    def get_by_ids(cls: Type[Model], doc_ids, *parent_ids) -> list[Model]:
        """Fetch documents from firestore by doc_ids

        Args:
            doc_ids (list[str]): List of document id
            *parent_ids (list[str]): List of parent_id defined by :attr:`COLLECTION_PATH_PARAMS`
        Returns:
            list: list of model instance
        """
        if len(doc_ids) == 0:
            return []
        coll = cls.get_client().collection(cls._get_col_path_by_ids(*parent_ids))
        doc_refs = [coll.document(doc_id) for doc_id in doc_ids]
        objs = []
        for doc in cls.get_client().get_all(doc_refs):
            obj = cls(doc.id, *parent_ids)
            obj._from_db_dict(doc.to_dict())
            objs.append(obj)
        return objs

    def put(self, exclude=[], only=None, **kwargs):
        """Save instance values to firestore

        If :attr:`doc_id` is `None`, create new Document.
        If :attr:`doc_id` is not `None`, update existing Document.

        Args:
            exclude (list[str], optional): If specified, save property not listed.
            only (list[str], optional): If specified, save property only listed.
            **kwargs: extra arguments pass to before_put, after_put
        """
        self._validate()
        self.validate()
        if self.before_put(**kwargs):
            db_dict = self._to_db_dict(exclude=exclude, only=only)
            coll_ref = self.get_client().collection(self._get_col_path())
            if self._doc_id:
                if len(exclude) > 0 or only:
                    coll_ref.document(self._doc_id).update(db_dict)
                else:
                    # [memo] .set will remove all fields not in db_dict
                    coll_ref.document(self._doc_id).set(db_dict)
                self.after_put(False, **kwargs)
            else:
                _, doc_ref = coll_ref.add(db_dict)
                self._doc_id = doc_ref.id
                self.after_put(True, **kwargs)

    def before_put(self, **kwargs):
        """Hook before :func:`put` and return whether continue to put or not

        Returns:
            bool: whether continue to put or not
        """
        # createかupdateは self._doc_id の有無で確認
        return True

    def after_put(self, created, **kwargs):
        """Hook after :func:`put` succeeded.

        Args:
            created (bool, optional): True if  :func:`put` created new document else False
            **kwargs: extra arguments passed from :func:`put`
        """
        pass

    def delete(self):
        """Delete document in firestore"""
        if self.is_deletable() and self.before_delete():
            self.get_client().collection(self._get_col_path()).document(
                self._doc_id
            ).delete()
            self.after_delete()

    def is_deletable(self) -> bool:
        """Determine whether continue to :func:`delete` or not.

        Returns:
            bool: continue to :func:`delete` or not
        """
        return True

    def before_delete(self):
        """Hook before :func:`delete` and return whether continue to :func:`delete` or not.

        Returns:
            bool: continue to :func:`delete` or not
        """
        return True

    def after_delete(self):
        """Hook after :func:`delete` succeeded."""
        pass

    def delete_all(self):
        """Delete document and subcollection recursively"""
        if self.is_deletable() and self.before_delete():
            doc = (
                self.get_client()
                .collection(self._get_col_path())
                .document(self._doc_id)
            )
            self._delete_doc_recursive(doc)
            self.after_delete()

    @classmethod
    def _delete_doc_recursive(cls, doc):
        for collection in doc.collections():
            for child_doc in collection.list_documents():
                cls._delete_doc_recursive(child_doc)
        doc.delete()

    @classmethod
    def where(
        cls,
        conds,
        *parent_ids,
        to_dict=False,
        order_by=None,
        limit=100,
        offset=None,
        collection_id=None
    ):
        """Fetch documents which match the conditions.

        Args:
            conds (list[]): List of search conditions. Each condition must be list of [`field`, `operator`, `value`]. Each condition is passed to firestore .where() method.
            *parent_ids (list[str]): List of parent_id defined by :attr:`COLLECTION_PATH_PARAMS`
            to_dict (bool): Return list of dict instead of model instance if set True.
            order_by (str): Property name to sort the results. Add "-" prefix if descending order, like "-price".
            limit (int): Number of max documents.
            offset (int): Number of offset to fetch the documents.
            collection_id (str): Set collection name to search by collection_group. If collection_id is specified, parent_ids are ignored.
        Returns:
            list: instances or dicts of the model
        """

        if collection_id:
            # https://github.com/googleapis/google-cloud-python/blob/4fd18c8aef86c287f50780036c0751f965c6e227/firestore/google/cloud/firestore_v1/client.py#L198
            docs = cls.get_client().collection_group(collection_id)
        else:
            docs = cls.get_client().collection(cls._get_col_path_by_ids(*parent_ids))
        for field, operator, value in conds:
            prop = cls._properties.get(field)
            if prop:
                value = prop.to_db_search_value(value)
            docs = docs.where(field, operator, value)
        if order_by:
            for order_by_cond in order_by.split(","):
                if order_by_cond.startswith("-"):
                    order_by_cond = order_by_cond[1:]
                    direction = "DESCENDING"
                else:
                    direction = "ASCENDING"
                docs = docs.order_by(order_by_cond, direction=direction)
        if limit:
            docs = docs.limit(limit)
        if offset:
            docs = docs.offset(offset)
        results = []
        for doc in docs.stream():
            if collection_id:
                parent_ids = cls._parent_ids_from_path(doc.reference.path)
                obj = cls(doc.id, *parent_ids)
            else:
                obj = cls(doc.id, *parent_ids)
            obj._from_db_dict(doc.to_dict())
            if not to_dict:
                results.append(obj)
            else:
                results.append(obj.to_dict())
        return results

    @classmethod
    def all(cls, *parent_ids, **kwargs):
        """Fetch all documents.

        Args:
            *parent_ids: Same as :func:`where`
            **kwargs: Same as :func:`where`
        Returns:
            list: instances of the model
        """
        return cls.where([], *parent_ids, **kwargs)

    @classmethod
    def stream(cls, *parent_ids, conds=[], collection_id=None):
        """Generator for all documents.

        Args:
            *parent_ids: Same as :func:`where`
            conds (list[]): Same as :func:`where`
            collection_id (str): Same as :func:`where`
        Returns:
            generator: yield instances of the model
        """
        if collection_id:
            docs = cls.get_client().collection_group(collection_id)
        else:
            docs = cls.get_client().collection(cls._get_col_path_by_ids(*parent_ids))
        for field, operator, value in conds:
            prop = cls._properties.get(field)
            if prop:
                value = prop.to_db_search_value(value)
            docs = docs.where(field, operator, value)
        for doc in docs.stream():
            if collection_id:
                parent_ids = cls._parent_ids_from_path(doc.reference.path)
                obj = cls(doc.id, *parent_ids)
            else:
                obj = cls(doc.id, *parent_ids)
            obj._from_db_dict(doc.to_dict())
            yield (obj)

    @classmethod
    def to_schema(cls):
        """Generate JsonSchema definition for the model

        Returns:
            dict: JsonSchema definition
        """
        required = []
        props = {
            "id": {
                "type": "string",
            }
        }
        for k in cls._properties.keys():
            prop = cls._properties[k]
            if prop.required:
                required.append(prop._name)
            if prop._name:
                props[prop._name] = prop._get_schema()
        required.sort()
        schema = {
            "type": "object",
            "required": required,
            "properties": props,
        }
        return schema
