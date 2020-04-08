import copy
from collections import OrderedDict
from collections.abc import Mapping
from google.protobuf import json_format

from binwen.exceptions import ConfigException, ValidationError, SkipFieldException
from binwen.utils.functional import import_obj
from binwen.serializers.fields import Field, empty

LIST_SERIALIZER_KWARGS = (
    'required', 'default', 'initial', 'source', 'partial',
    'instance', 'form_data', 'allow_empty', 'allow_null'
)


def set_value(dictionary, keys, value):
    """
    类似于Python内置的字典`dictionary[key] = value`，
    但是需要一个嵌套键的列表，而不是一个键。

    set_value({'a': 1}, [], {'b': 2}) -> {'a': 1, 'b': 2}
    set_value({'a': 1}, ['x'], 2) -> {'a': 1, 'x': 2}
    set_value({'a': 1}, ['x', 'y'], 2) -> {'a': 1, 'x': {'y': 2}}
    """
    if not keys:
        dictionary.update(value)
        return

    for key in keys[:-1]:
        if key not in dictionary:
            dictionary[key] = {}
        dictionary = dictionary[key]

    dictionary[keys[-1]] = value


class BaseFormSerializer(Field):

    def __init__(self, instance=None, request_data=empty, **kwargs):
        self.instance = instance
        self._request_data = request_data
        self.partial = kwargs.pop('partial', False)
        self._context = kwargs.pop('context', {})
        kwargs.pop('many', None)
        super(BaseFormSerializer, self).__init__(**kwargs)

    def __new__(cls, *args, **kwargs):
        if kwargs.pop('many', False):
            return cls.many_init(*args, **kwargs)
        return super().__new__(cls, *args, **kwargs)

    @classmethod
    def many_init(cls, *args, **kwargs):
        allow_empty = kwargs.pop('allow_empty', None)
        child_serializer = cls(*args, **kwargs)
        list_kwargs = {'child': child_serializer}
        if allow_empty is not None:
            list_kwargs['allow_empty'] = allow_empty
        list_kwargs.update({k: v for k, v in kwargs.items() if k in LIST_SERIALIZER_KWARGS})
        list_serializer_class = getattr(getattr(cls, 'Meta', None), 'list_serializer_class', ListSerializer)
        return list_serializer_class(*args, **list_kwargs)

    def is_valid(self, raise_exc=False):
        if not hasattr(self, '_validated_data'):
            try:
                self._validated_data = self.run_validation(self._request_data)
            except ValidationError as exc:
                self._validated_data = {}
                self._errors = exc.details
            else:
                self._errors = None

        if self._errors and raise_exc:
            raise ValidationError(self._errors)

        return not bool(self._errors)

    def run_validation(self, data):
        is_empty_value, data = self.validate_empty_values(data)
        if is_empty_value:
            return data

        value = self.to_internal_value(data)
        try:
            self.run_validators(value)
            value = self.clean(value)
        except ValidationError as exc:
            raise ValidationError(exc.details)

        return value

    def get_validators(self):
        validators = getattr(getattr(self, 'Meta', None), 'validators', None)
        return list(validators) if validators is not None else ()

    def get_initial(self):
        if self._request_data is not empty:
            if not isinstance(self._request_data, Mapping):
                return OrderedDict()

            return OrderedDict([
                (field_name, field.get_value(self._request_data))
                for field_name, field in self.fields.items()
                if field.get_value(self._request_data) is not empty
            ])

        return OrderedDict([(field.field_name, field.get_initial()) for field in self.fields.values()])

    @property
    def data(self):
        if self._request_data is not empty and not hasattr(self, '_validated_data'):
            msg = (
                'When a serializer is passed a `request_data` keyword argument you '
                'must call `.is_valid()` before attempting to access the '
                'serialized `.data` representation.\n'
                'You should either call `.is_valid()` first.'
            )
            raise AssertionError(msg)

        if not hasattr(self, '_data'):
            if self.instance is not None and not getattr(self, '_errors', None):
                self._data = self.to_representation(self.instance)
            elif hasattr(self, '_validated_data') and not getattr(self, '_errors', None):
                self._data = self.validated_data
            else:
                self._data = self.get_initial()
        return self._data

    @property
    def pb(self):
        if not self.proto_message:
            raise ConfigException("Serializer Meta `proto_message` is a required option")

        if not hasattr(self, '_pb'):
            self._pb = json_format.ParseDict(self.data, self.proto_message(), ignore_unknown_fields=True)

        return self._pb

    @property
    def errors(self):
        if not hasattr(self, '_errors'):
            msg = 'You must call `.is_valid()` before accessing `.errors`.'
            raise AssertionError(msg)
        return self._errors

    @property
    def fields(self):
        if not hasattr(self, '_fields'):
            self._fields = OrderedDict()
            fields = copy.deepcopy(self.base_fields)
            for fn, field in fields.items():
                field.bind(field_name=fn, parent=self)
                self._fields[fn] = field
        return self._fields

    def to_internal_value(self, data):

        # if not isinstance(data, Mapping):
        #     self.fail('invalid', datatype=type(data).__name__)

        ret = OrderedDict()
        errors = OrderedDict()

        for field_name, field in self.fields.items():
            validate_method = getattr(self, f'clean_{field_name}', None)
            primitive_value = field.get_value(data)
            try:
                validated_value = field.run_validation(primitive_value)
                if validate_method is not None:
                    validated_value = validate_method(validated_value)
            except ValidationError as exc:
                errors[field.field_name] = exc.details
            except SkipFieldException:
                pass
            else:
                set_value(ret, field.source_attrs, validated_value)

        if errors:
            raise ValidationError(errors)

        return ret

    def to_representation(self, instance):
        ret = OrderedDict()
        for field_name, field in self.fields.items():
            try:
                attribute = field.get_attribute(instance)
            except SkipFieldException:
                continue

            attr_data = field.to_representation(attribute)
            clean_method = f'clean_{field_name}'
            if hasattr(self, clean_method):
                attr_data = getattr(self, clean_method)(instance, attr_data)
            ret[field_name] = attr_data

        cleaned_data = self.clean(ret)
        if cleaned_data is not None:
            ret = cleaned_data

        return ret

    @property
    def validated_data(self):
        if not hasattr(self, '_validated_data'):
            msg = 'You must call `.is_valid()` before accessing `.validated_data`.'
            raise AssertionError(msg)
        return self._validated_data

    def clean(self, ret):
        return ret


class DeclarativeFieldsMetaclass(type):
    @classmethod
    def _get_declared_fields(cls, bases, attrs):
        fields = [(fn, attrs.pop(fn)) for fn, obj in list(attrs.items()) if isinstance(obj, Field)]

        for base in reversed(bases):
            if hasattr(base, 'declared_fields'):
                fields += [(fn, obj) for fn, obj in base.declared_fields.items() if fn not in attrs]

        return OrderedDict(fields)

    def __new__(cls, name, bases, attrs):
        declared_fields = cls._get_declared_fields(bases, attrs)
        attrs['declared_fields'] = declared_fields
        new_class = super(DeclarativeFieldsMetaclass, cls).__new__(cls, name, bases, attrs)
        new_class.proto_message = import_obj(getattr(getattr(new_class, 'Meta', None), "proto_message", None))
        new_class.base_fields = declared_fields
        new_class.declared_fields = declared_fields
        return new_class


class Serializer(BaseFormSerializer, metaclass=DeclarativeFieldsMetaclass):
    default_error_messages = {
        'invalid': 'Invalid data. Expected a dictionary, but got {datatype}.'
    }


class ListSerializer(BaseFormSerializer):
    many = True

    default_error_messages = {
        'not_a_list': 'Expected a list of items but got type "{input_type}".',
        'empty': 'This list may not be empty.'
    }

    def __init__(self, child, *args, **kwargs):
        self.child = child
        self.allow_empty = kwargs.pop('allow_empty', True)
        super().__init__(*args, **kwargs)
        self.child.bind(field_name='', parent=self)

    def bind(self, field_name, parent):
        super().bind(field_name, parent)
        self.partial = self.parent.partial

    def get_initial(self):
        if self._request_data is not empty:
            return self.to_representation(self._request_data)
        return []

    def to_internal_value(self, data):

        if not isinstance(data, list):
            self.fail('not_a_list', input_type=type(data).__name__)

        if not self.allow_empty and len(data) == 0:
            if self.parent and self.partial:
                raise SkipFieldException()

            self.fail('empty')

        ret = []
        errors = []

        for item in data:
            try:
                validated = self.child.run_validation(item)
            except ValidationError as exc:
                errors.append(exc.details)
            else:
                ret.append(validated)

        if any(errors):
            raise ValidationError(errors)

        return ret

    def to_representation(self, data):
        return [self.child.to_representation(item) for item in data]

    @property
    def data(self):
        ret = super(ListSerializer, self).data
        return ret

    def is_valid(self, raise_exception=False):
        if not hasattr(self, '_validated_data'):
            try:
                self._validated_data = self.run_validation(self._request_data)
            except ValidationError as exc:
                self._validated_data = []
                self._errors = exc.details
            else:
                self._errors = None

        if self._errors and raise_exc:
            raise ValidationError(self._errors)

        return not bool(self._errors)
