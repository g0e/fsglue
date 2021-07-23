import jsonschema
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from datetime import datetime
import json
import copy
from .exceptions import FsglueProgrammingError, FsglueValidationError
from enum import Enum
from typing import Optional, Any, TypeVar, Generic, Union, Sequence


PropertySpecialValue = Enum("PropertySpecialValue", "SET_NOTHING")
T = TypeVar('T')


class BaseProperty(Generic[T]):
    """BasePropety

    You can define your CustomProperty by extending this BaseProperty.

    Examples:
        .. code-block:: python

            import fsglue

            class YesNoProperty(fsglue.BaseProperty):
                # Return 'Yes' or 'No' for application and store True or False in firestore

                def to_app_value(self, value, obj):
                    return 'Yes' if bool(value) else 'No'

                def from_app_value(self, value):
                    return True if value == 'Yes' else False

                def to_db_value(self, value, obj):
                    return bool(value)

                def from_db_value(self, value):
                    return bool(value)

                def get_schema(self):
                    return {"type": "string", "enum": ["Yes", "No"]}
    """
    _name: Optional[str]
    required: bool
    default: Any
    choices: Optional[Sequence[Any]]
    schema: Optional[dict]
    validator: Any
    is_virtual: bool

    _INTACT_PREFIX = "___"

    def __init__(
        self,
        required: bool = False,
        default: Any = None,
        choices: Optional[Sequence[Any]] = None,
        schema: Optional[dict] = None,
        validator: Any = None,
        is_virtual: bool = False,
    ):
        """Constructor

        Args:
            required (bool, optional): If True, property value cannot be None
            default (optional): If property value is None, property return this default value
            choices (list, optional): List of values that property value can take
            schema (dict, optional): JsonSchema definition for property.
            validator (Callable[[value, obj], None], optional): value validator for property
            is_virtual (bool, optional): If True, do not save property value in firestore.
        """
        self._name = None
        self.required = required
        self.default = default
        self.choices = choices
        self.schema = schema
        self.validator = validator
        self.is_virtual = is_virtual  # don't save to firestore if True

    def _fix_up(self, cls, name: str):
        if self._name is None:
            self._name = name

    def __get__(self, obj, objtype=None) -> T:
        if obj is None:
            return self  # type: ignore  # __get__ called on class
        return self._get_app_value(obj)

    def __set__(self, obj, value: T):
        self._set_app_value(obj, value)

    def _get_app_value(self, obj, get_intact=False) -> T:
        """Get exposed value for application"""
        if self._name is None:
            raise Exception("property not fixed")
        if not get_intact:
            v = obj._doc_values.get(self._name)
        else:
            v = obj._doc_values.get(self._INTACT_PREFIX + self._name)
        if v is None and self.default is not None:
            v = self.default
        return self.to_app_value(v, obj)

    def to_app_value(self, value, obj):
        """Convert property-internal value to exposed value for application

        Args:
            value: property-internal value
            obj: model instance
        Returns:
            exposed value
        """
        return value

    def _set_app_value(self, obj, value):
        """Set exposed value from application"""
        self._validate(value, obj)
        value = self.from_app_value(value, obj)
        if not (value == PropertySpecialValue.SET_NOTHING):
            obj._doc_values[self._name] = value

    def from_app_value(self, value, obj):
        """Convert exposed value to property-internal value from application

        Args:
            value: exposed value
            obj: model instance
        Returns:
            property-internal value
        """
        return value

    def _get_db_value(self, obj):
        """Get firestore value"""
        value = obj._doc_values.get(self._name)
        return self.to_db_value(value, obj)

    def to_db_value(self, value, obj):
        """Convert property-internal value to firestore value

        Args:
            value: property-internal value
            obj: model instance
        Returns:
            firestore value
        """
        return value

    def _set_db_value(self, obj, value):
        """Set firestore value"""
        value = self.from_db_value(value, obj)
        if self._name is None:
            raise Exception("property not fixed")
        if not (value == PropertySpecialValue.SET_NOTHING):
            obj._doc_values[self._name] = value
            if isinstance(value, dict) or isinstance(value, list):
                value = copy.deepcopy(value)
            obj._doc_values[self._INTACT_PREFIX + self._name] = value

    def from_db_value(self, value, obj):
        """Convert firestore value to internal value

        Args:
            value: firestore value
            obj: model instance
        Returns:
            property-internal value
        """
        return value

    def to_db_search_value(self, value):
        """Convert exposed value to firestore value for where/all method"""
        return self.to_db_value(self.from_app_value(value, None), None)

    def _get_change(self, obj):
        """Get before and after value from it was retrieved from firestore. If not change, return `None`."""
        before = self._get_app_value(obj, get_intact=True)
        after = self._get_app_value(obj)
        if before == after:
            return None
        else:
            return {"before": before, "after": after}

    def _validate(self, value, obj):
        if self.choices is not None and value not in self.choices:
            raise FsglueValidationError("{0} not found in choices".format(value))
        if self.required and value is None:
            raise FsglueValidationError("{0} is required".format(self._name))
        if self.schema and value is not None:
            try:
                jsonschema.validate(value, self.schema)
            except JsonSchemaValidationError as e:
                raise FsglueValidationError(str(e))
        if self.validator:
            # should raise Exception if invalid
            self.validator(value, obj)

    def _get_schema(self):
        if self.schema:
            schema = copy.deepcopy(self.schema)
        else:
            schema = self.get_schema()
        if self.default and not (schema.get("default")):
            schema["default"] = self.default
        # if self.choices:
        #     schema["enum"] = self.choices
        return schema

    def get_schema(self):
        """Get JsonSchema definition for property

        Args:
            value: property firestore value
        Returns:
            property inside value
        """
        return {}


class StringProperty(BaseProperty[str]):
    def to_app_value(self, value, obj):
        return str(value) if value is not None else None

    def from_app_value(self, value, obj):
        return str(value) if value is not None else None

    def to_db_value(self, value, obj):
        return str(value) if value is not None else None

    def from_db_value(self, value, obj):
        return str(value) if value is not None else None

    def get_schema(self):
        return {"type": "string"}


class IntegerProperty(BaseProperty[int]):
    def to_app_value(self, value, obj):
        return int(value) if value is not None else None

    def from_app_value(self, value, obj):
        return int(value) if value is not None else None

    def to_db_value(self, value, obj):
        return int(value) if value is not None else None

    def from_db_value(self, value, obj):
        return int(value) if value is not None else None

    def get_schema(self):
        return {"type": "number"}


class FloatProperty(BaseProperty[float]):
    def to_app_value(self, value, obj):
        return float(value) if value is not None else None

    def from_app_value(self, value, obj):
        return float(value) if value is not None else None

    def to_db_value(self, value, obj):
        return float(value) if value is not None else None

    def from_db_value(self, value, obj):
        return float(value) if value is not None else None

    def get_schema(self):
        return {"type": "number"}


class BooleanProperty(BaseProperty[bool]):
    def to_app_value(self, value, obj):
        return bool(value) if value is not None else None

    def from_app_value(self, value, obj):
        return bool(value) if value is not None else None

    def to_db_value(self, value, obj):
        return bool(value) if value is not None else None

    def from_db_value(self, value, obj):
        return bool(value) if value is not None else None

    def get_schema(self):
        return {"type": "boolean"}


class TimestampProperty(BaseProperty[Union[int, float]]):
    """Provide UTC Timestamp(int) value for application and Date value for firestore"""

    def __init__(self, auto_now=False, auto_now_add=False, **kwargs):
        """Constructor

        Args:
            auto_now (bool, optional): If True, store last updated time
            auto_now_add (bool, optional): If True, store created time
            **kwargs(optional): Same as :func:`BaseProperty.__init__`
        """
        super().__init__(**kwargs)
        self._auto_now = auto_now
        self._auto_now_add = auto_now_add

    def to_app_value(self, value, obj):
        return value

    def from_app_value(self, value, obj):
        # If auto_now or auto_now_add is True, skip set value
        if self._auto_now or self._auto_now_add:
            return PropertySpecialValue.SET_NOTHING
        return value

    def to_db_value(self, value, obj):
        # Store utc datetime in firestore
        if self._auto_now:
            return datetime.utcnow()
        if self._auto_now_add and value is None:
            return datetime.utcnow()
        if value is not None:
            return datetime.utcfromtimestamp(value)
        else:
            return None

    def from_db_value(self, value, obj):
        # Store unixtime at inside
        if value is not None:
            value = value.timestamp()
        return value

    def to_db_search_value(self, value):
        if value is not None:
            value = datetime.utcfromtimestamp(int(value))
        return value

    def get_schema(self):
        return {"type": "number"}


class JsonProperty(BaseProperty[T]):
    """Can store dict or list value for application and firestore.

    Examples:
        .. code-block:: python

            import fsglue

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

            # create
            purchase = Purchase.create()
            purchase.items = [{"name": "apple", "price": 100, "cnt": 1}]
            purchase.coupon = {
                "coupon_id": "test",
                "coupon_name": "time sale 10% off",
                "condition": {"discount_rate": 0.9},
            }
            purchase.put()
    """

    def __init__(self, store_as_string=False, **kwargs):
        """Constructor

        Args:
            _store_as_string (bool, optional): If True, store value as string in firestore.
            **kwargs(optional): Same as :func:`BaseProperty.__init__`
        """
        super().__init__(**kwargs)
        self._store_as_string = store_as_string

    def to_app_value(self, value, obj):
        return value

    def from_app_value(self, value, obj):
        return value

    def to_db_value(self, value, obj):
        if self._store_as_string:
            value = json.dumps(value)
        return value

    def from_db_value(self, value, obj):
        if value is not None:
            if self._store_as_string:
                value = json.loads(value)
        return value

    def get_schema(self):
        return {"type": "object"}


class ComputedProperty(BaseProperty[T]):
    """Can store computed value from other property values.

    Examples:
        .. code-block:: python

            import fsglue

            def calc_sum(obj):
                return obj.num1 + obj.num2

            class TestModel(fsglue.BaseModel):
                COLLECTION_PATH = "test"
                COLLECTION_PATH_PARAMS = []

                num1 = fsglue.IntegerProperty(required=True)
                num2 = fsglue.IntegerProperty(required=True)
                sum = fsglue.ComputedProperty(computer=calc_sum)

    """

    def __init__(self, computer=None, **kwargs):
        """Constructor

        Args:
            computer (Callable[[obj], Any]): Calculate property value from other propery values
            **kwargs(optional): Same as :func:`BaseProperty.__init__`
        """
        super().__init__(**kwargs)
        if computer is None:
            raise FsglueProgrammingError("computer is required")
        self._computer = computer

    def to_app_value(self, value, obj):
        return self._computer(obj)

    def from_app_value(self, value, obj):
        return PropertySpecialValue.SET_NOTHING

    def to_db_value(self, value, obj):
        return self._computer(obj)

    def from_db_value(self, value, obj):
        return PropertySpecialValue.SET_NOTHING

    def to_db_search_value(self, value):
        return value

    def get_schema(self):
        raise FsglueProgrammingError("schema must be specified")


class ConstantProperty(BaseProperty[T]):
    """Provide constant value for application and firestore"""

    def __init__(self, value=None, **kwargs):
        """Constructor

        Args:
            value: constant value
            **kwargs(optional): Same as :func:`BaseProperty.__init__`
        """
        super().__init__(**kwargs)
        if value is None:
            raise FsglueProgrammingError("value is required")
        self._value = value

    def to_app_value(self, value, obj):
        return self._value

    def from_app_value(self, value, obj):
        return PropertySpecialValue.SET_NOTHING

    def to_db_value(self, value, obj):
        return self._value

    def from_db_value(self, value, obj):
        return PropertySpecialValue.SET_NOTHING

    def to_db_search_value(self, value):
        return value

    def get_schema(self):
        raise FsglueProgrammingError("schema must be specified")
