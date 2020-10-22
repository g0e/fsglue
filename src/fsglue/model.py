# inspired by https://github.com/GoogleCloudPlatform/datastore-ndb-python/blob/master/ndb/model.py
from .client import get_client
from .exceptions import FsglueValidationError
import re
from .property import BaseProperty


class MetaModel(type):

    def __init__(cls, name, bases, classdict):
        super(MetaModel, cls).__init__(name, bases, classdict)
        cls._fix_up_properties()


class BaseModel(object, metaclass=MetaModel):
    """
    BaseModel
    """
    COLLECTION_PATH = None  # ex: category/{0}/group/{1}/page
    COLLECTION_PATH_PARAMS = []  # ex: ["category_id", "group_id"]
    DICT_ID_KEY = "id"
    ID_VALIDATION_PATTERN = r"^[a-zA-Z0-9_]+$"
    _properties = None

    @classmethod
    def _fix_up_properties(cls):
        cls._properties = {}
        for name in set(dir(cls)):
            prop = getattr(cls, name, None)
            if isinstance(prop, BaseProperty):
                prop._fix_up(cls, name)
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
    def to_schema(cls):
        """
        generate json schema definition
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
            props[prop._name] = prop._get_schema()
        required.sort()
        schema = {
            "required": required,
            "type": "object",
            "properties": props,
        }
        return schema

    @property
    def doc_id(self):
        return self._doc_id

    def to_dict(self, get_intact=False):
        """cast to dict
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
        "firestoreに保存する用のdictを取得して返却する"
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

    def from_dict(self, values={}):
        "アプリからdictでmodelに値を保存する"
        for k in self._properties.keys():
            if k in values:
                self._properties[k]._set_app_value(self, values[k])

    def _from_db_dict(self, values={}):
        "firestoreのdictからmodelに値を保存する"
        for k in self._properties.keys():
            prop = self._properties[k]
            if prop.is_virtual:
                continue
            if k in values:
                prop._set_db_value(self, values[k])

    @classmethod
    def _validate_doc_id(cls, doc_id):
        if cls.ID_VALIDATION_PATTERN:
            if not re.match(cls.ID_VALIDATION_PATTERN, doc_id):
                raise FsglueValidationError("invalid id: {0}".format(doc_id))

    def _validate(self):
        "_proppertiesを元にvalidationを行う。invalidな場合はValidationErrorをraiseする"
        for k in self._properties.keys():
            prop = self._properties[k]
            if hasattr(prop, "_get_validate_value"):
                value = prop._get_validate_value(self)
            else:
                value = prop._get_app_value(self)
            prop._validate(value)

    def validate(self):
        "必要に応じて継承先クラスで定義する。invalidな場合はValidationErrorをraiseする"
        pass

    def before_put(self, **kwargs):
        "更新前にhookする時に使う"
        # createかupdateは self._doc_id の有無で確認
        return True

    def put(self, exclude=[], only=None, **kwargs):
        self._validate()
        self.validate()
        if self.before_put(**kwargs):
            db_dict = self._to_db_dict(exclude=exclude, only=only)
            coll_ref = get_client().collection(self._get_col_path())
            if self._doc_id:
                if len(exclude) > 0 or only:
                    coll_ref.document(self._doc_id).update(db_dict)
                else:
                    # replace処理になるので含まれていないフィールドは削除される
                    coll_ref.document(self._doc_id).set(db_dict)
                self.after_put(False, **kwargs)
            else:
                _, doc_ref = coll_ref.add(db_dict)
                self._doc_id = doc_ref.id
                self.after_put(True, **kwargs)

    def after_put(self, created, **kwargs):
        "更新後にhookする時に使う"
        pass

    def is_deletable(self):
        "依存関係的に削除できるかどうかをチェックして、削除できない場合はValidationErrorをraiseする"
        return True

    def before_delete(self):
        "削除前にhookする時に使う。Falseを返すと削除しない"
        return True

    def delete(self):
        if self.is_deletable() and self.before_delete():
            get_client().collection(self._get_col_path()).document(self._doc_id).delete()
            self.after_delete()

    def delete_all(self):
        "subscollectionも含めて再帰的に削除"
        if self.is_deletable() and self.before_delete():
            doc = get_client().collection(self._get_col_path()).document(self._doc_id)
            self._delete_doc_recursive(doc)
            self.after_delete()

    @classmethod
    def _delete_doc_recursive(cls, doc):
        for collection in doc.collections():
            for child_doc in collection.list_documents():
                cls._delete_doc_recursive(child_doc)
        doc.delete()

    def after_delete(self):
        "削除後にhookする時に使う"
        pass

    @classmethod
    def get_by_id(cls, doc_id, *parent_ids):
        doc = get_client().collection(cls._get_col_path_by_ids(*parent_ids)).document(doc_id).get()
        if doc.exists:
            obj = cls(doc.id, *parent_ids)
            obj._from_db_dict(doc.to_dict())
            return obj
        return None

    @classmethod
    def get_by_ids(cls, doc_ids, *parent_ids):
        if len(doc_ids) == 0:
            return []
        coll = get_client().collection(cls._get_col_path_by_ids(*parent_ids))
        doc_refs = [coll.document(doc_id) for doc_id in doc_ids]
        objs = []
        for doc in get_client().get_all(doc_refs):
            obj = cls(doc.id, *parent_ids)
            obj._from_db_dict(doc.to_dict())
            objs.append(obj)
        return objs

    @classmethod
    def exists(cls, doc_id, *parent_ids):
        return get_client().collection(cls._get_col_path_by_ids(*parent_ids)).document(doc_id).get().exists

    @classmethod
    def create_by_dict(cls, values, *parent_ids, exclude=[], only=None, without_put=False):
        doc_id = values.get(cls.DICT_ID_KEY)
        if doc_id:
            cls._validate_doc_id(doc_id)
        doc_values = cls._filter_values(values, exclude=exclude, only=only)
        obj = cls(doc_id, *parent_ids)
        obj.from_dict(doc_values)
        if not without_put:
            obj.put()
        else:
            obj._validate()
            obj.validate()
        return obj

    @classmethod
    def update_by_dict(cls, values, *parent_ids, exclude=[], only=None, without_put=False):
        doc_id = values.get(cls.DICT_ID_KEY)
        if not doc_id:
            raise FsglueValidationError(cls.DICT_ID_KEY + " not found")
        new_values = cls._filter_values(values, exclude=exclude, only=only)
        obj = cls.get_by_id(doc_id, *parent_ids)
        obj.from_dict(new_values)
        if not without_put:
            obj.put(exclude=exclude, only=only)
        else:
            obj._validate()
            obj.validate()
        return obj

    @classmethod
    def upsert_by_dict(cls, values, *parent_ids, exclude=[], only=None, without_put=False):
        doc_id = values.get(cls.DICT_ID_KEY)
        if not doc_id:
            raise FsglueValidationError(cls.DICT_ID_KEY + " not found")
        if cls.exists(doc_id, *parent_ids):
            return cls.update_by_dict(values, *parent_ids, exclude=exclude, only=only, without_put=without_put)
        else:
            return cls.create_by_dict(values, *parent_ids, exclude=exclude, only=only, without_put=without_put)

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
        # parent_ids を path から抽出する(collection_groupの時に使う)
        parent_ids = []
        for key, value in zip(cls.COLLECTION_PATH.split("/"), path.split("/")):
            if key.startswith("{") and key.endswith("}"):
                parent_ids.append(value)
        return parent_ids

    @classmethod
    def where(cls, conds, *parent_ids, to_dict=False, order_by=None, limit=100, offset=None, collection_id=None):
        if collection_id:
            # collection group の機能を使ってquery投げる場合
            # https://github.com/googleapis/google-cloud-python/blob/4fd18c8aef86c287f50780036c0751f965c6e227/firestore/google/cloud/firestore_v1/client.py#L198
            docs = get_client().collection_group(collection_id)
        else:
            docs = get_client().collection(cls._get_col_path_by_ids(*parent_ids))
        for field, operator, value in conds:
            prop = cls._properties.get(field)
            if prop:
                value = prop.to_db_value(value)
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
    def stream(cls, *parent_ids, conds=[], collection_id=None):
        "whereとallのgenerator版(メモリ節約版)"
        if collection_id:
            docs = get_client().collection_group(collection_id)
        else:
            docs = get_client().collection(cls._get_col_path_by_ids(*parent_ids))
        for field, operator, value in conds:
            prop = cls._properties.get(field)
            if prop:
                value = prop.to_db_value(value)
            docs = docs.where(field, operator, value)
        for doc in docs.stream():
            if collection_id:
                parent_ids = cls._parent_ids_from_path(doc.reference.path)
                obj = cls(doc.id, *parent_ids)
            else:
                obj = cls(doc.id, *parent_ids)
            obj._from_db_dict(doc.to_dict())
            yield(obj)

    @classmethod
    def all(cls, *parent_ids, **kwargs):
        return cls.where([], *parent_ids, **kwargs)
