import jsonschema
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from datetime import datetime
import json
import copy
from .exceptions import FirestoreGlueProgrammingError, FirestoreGlueValidationError


class BaseProperty(object):

    INTACT_PREFIX = "___"

    def __init__(self, required=False, default=None, choices=None, schema=None, validator=None, is_virtual=False):
        self._name = None
        self.required = required
        self.default = default
        self.choices = choices
        # JsonSchemaによるvalidation用(理論上はJsonProperty以外でも使える)
        self.schema = schema
        self.validator = validator
        self.is_virtual = is_virtual  # True の場合はFirestore側に保存しない

    def _fix_up(self, cls, name):
        if self._name is None:
            self._name = name

    def _get_app_value(self, obj, get_intact=False):
        "アプリで使う用のvalueをmodelから取得する時に使う"
        if not get_intact:
            v = obj._doc_values.get(self._name)
        else:
            v = obj._doc_values.get(self.INTACT_PREFIX + self._name)
        if v is None and self.default is not None:
            v = self.default
        return v

    def _set_app_value(self, obj, value):
        "アプリからvalueを設定してmodelに設定する時に使う"
        self._validate(value)
        obj._doc_values[self._name] = value

    def _get_db_value(self, obj):
        "firestoreに保存する用のvalueをmodelから取得する時に使う"
        return obj._doc_values.get(self._name)

    def _set_db_value(self, obj, value):
        "firestoreからvalueを取り出してmodelに保存する時に使う"
        obj._doc_values[self._name] = value
        if isinstance(value, dict) or isinstance(value, list):  # objectの場合は参照を切るためにdeepcopyする
            value = copy.deepcopy(value)
        obj._doc_values[self.INTACT_PREFIX + self._name] = value

    def _get_change(self, obj):
        "firestoreに保存されている値から変更があれば変更前の値(dict形式)を、変更がなければNoneを返却"
        before = self._get_app_value(obj, get_intact=True)
        after = self._get_app_value(obj)
        if before == after:
            return None
        else:
            return {"before": before, "after": after}

    def to_db_value(self, app_value):
        "valueをfirestoreに保存する値の形式に変換して返却(各Propertyで上書きする。whereとかで使う用)"
        return app_value

    def _validate(self, value):
        if self.choices is not None and value not in self.choices:
            raise FirestoreGlueValidationError(
                "{0} not found in choices".format(value))
        if self.required and value is None:
            raise FirestoreGlueValidationError(
                "{0} is required".format(self._name))
        if self.schema:
            try:
                jsonschema.validate(value, self.schema)
            except JsonSchemaValidationError as e:
                raise FirestoreGlueValidationError(str(e))
        if self.validator:
            # invalidな場合はvalidatorの中からValidationErrorをraiseする仕様
            self.validator(value)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self  # __get__ called on class
        return self._get_app_value(obj)

    def __set__(self, obj, value):
        self._set_app_value(obj, value)

    def _get_schema(self):
        if self.schema:
            schema = copy.deepcopy(self.schema)
        else:
            schema = {}
        if self.default:
            schema["default"] = self.default
        # if self.choices:
        #     schema["enum"] = self.choices
        return schema


class StringProperty(BaseProperty):

    def _get_app_value(self, obj, **kwargs):
        value = super()._get_app_value(obj, **kwargs)
        return str(value) if value is not None else None

    def _set_app_value(self, obj, value):
        if value is not None:
            value = str(value)
        super()._set_app_value(obj, value)

    def to_db_value(self, app_value):
        if app_value is not None:
            app_value = str(app_value)
        return app_value

    def _get_schema(self):
        schema = super()._get_schema()
        schema["type"] = "string"
        return schema


class IntegerProperty(BaseProperty):

    def _get_app_value(self, obj, **kwargs):
        value = super()._get_app_value(obj, **kwargs)
        return int(value) if value is not None else None

    def _set_app_value(self, obj, value):
        if value is not None:
            value = int(value)
        super()._set_app_value(obj, value)

    def to_db_value(self, app_value):
        if app_value is not None:
            app_value = int(app_value)
        return app_value

    def _get_schema(self):
        schema = super()._get_schema()
        schema["type"] = "number"
        return schema


class FloatProperty(BaseProperty):

    def _get_app_value(self, obj, **kwargs):
        value = super()._get_app_value(obj, **kwargs)
        return float(value) if value is not None else None

    def _set_app_value(self, obj, value):
        if value is not None:
            value = float(value)
        super()._set_app_value(obj, value)

    def to_db_value(self, app_value):
        if app_value is not None:
            app_value = float(app_value)
        return app_value

    def _get_schema(self):
        schema = super()._get_schema()
        schema["type"] = "number"
        return schema


class BooleanProperty(BaseProperty):

    def _get_app_value(self, obj, **kwargs):
        value = super()._get_app_value(obj, **kwargs)
        return bool(value) if value is not None else None

    def _set_app_value(self, obj, value):
        if value is not None:
            value = bool(value)
        super()._set_app_value(obj, value)

    def to_db_value(self, app_value):
        if app_value is not None:
            app_value = bool(app_value)
        return app_value

    def _get_schema(self):
        schema = super()._get_schema()
        schema["type"] = "boolean"
        return schema


class TimestampProperty(BaseProperty):

    def __init__(self, auto_now=False, auto_now_add=False, **kwargs):
        super().__init__(**kwargs)
        self._auto_now = auto_now
        self._auto_now_add = auto_now_add

    def _get_db_value(self, obj):
        "firestoreにはutcのdatetime型で保存"
        if self._auto_now:
            return datetime.utcnow()
        value = super()._get_db_value(obj)
        if self._auto_now_add and value is None:
            return datetime.utcnow()
        if value is not None:
            return datetime.utcfromtimestamp(value)
        else:
            return None

    def _set_db_value(self, obj, value):
        "app用にはunixtimeで保存"
        if value is not None:
            value = value.timestamp()
        super()._set_db_value(obj, value)

    def _set_app_value(self, obj, value):
        "auto_now=True, auto_now_add=Trueの場合は上書きしない"
        if self._auto_now or self._auto_now_add:
            return
        super()._set_app_value(obj, value)

    def to_db_value(self, app_value):
        if app_value is not None:
            app_value = datetime.utcfromtimestamp(int(app_value))
        return app_value

    def _get_schema(self):
        schema = super()._get_schema()
        schema["type"] = "number"
        return schema


class JsonProperty(BaseProperty):

    def __init__(self, store_as_string=False, **kwargs):
        super().__init__(**kwargs)
        self._store_as_string = store_as_string

    def _get_db_value(self, obj):
        value = super()._get_db_value(obj)
        if self._store_as_string:
            value = json.dumps(value)
        return value

    def _set_db_value(self, obj, value):
        if value is not None:
            if self._store_as_string:
                value = json.loads(value)
        super()._set_db_value(obj, value)

    def _get_schema(self):
        schema = super()._get_schema()
        if not schema.get("type"):
            schema["type"] = "object"
        return schema


class ComputedProperty(BaseProperty):

    def __init__(self, computer=None, **kwargs):
        super().__init__(**kwargs)
        self._computer = computer  # computerはobj=instanceを受け取って戻り値を計算

    def _get_app_value(self, obj, **kwargs):
        return self._computer(obj)

    def _set_app_value(self, obj, value):
        pass

    def _get_db_value(self, obj):
        return self._computer(obj)

    def _set_db_value(self, obj, value):
        pass

    def to_db_value(self, app_value):
        return app_value  # ここを変更する場合はUserDefinedCollectionBaseも修正が必要

    def _get_schema(self):
        if self.schema:
            return self.schema
        else:
            raise FirestoreGlueProgrammingError("schema must be specified")


class ConstantProperty(BaseProperty):

    def __init__(self, value=None, **kwargs):
        super().__init__(**kwargs)
        self._value = value

    def _get_app_value(self, obj, **kwargs):
        return self._value

    def _set_app_value(self, obj, value):
        pass

    def _get_db_value(self, obj):
        return self._value

    def _set_db_value(self, obj, value):
        pass

    def _get_schema(self):
        if self.schema:
            return self.schema
        else:
            raise FirestoreGlueProgrammingError("schema must be specified")
