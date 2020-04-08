import re
import pendulum
import copy
import datetime
from collections import OrderedDict
from collections.abc import Mapping

from binwen.exceptions import SkipFieldException, ValidationError
from binwen.utils.functional import get_attribute, to_choices_dict, flatten_choices_dict
from binwen.serializers.validators import MinLengthValidator, MaxLengthValidator, MaxValueValidator, MinValueValidator

__all__ = [
    'Field', 'BooleanField', 'NullBooleanField', 'CharField',
    'IntegerField', 'FloatField', 'DateTimeField', 'DateField', 'TimeField',
    'ChoiceField', 'ListField', 'SerializerMethodField', 'empty'
]

empty = object()


class Field:
    default_validators = []
    default_error_messages = {
        'required': 'This field is required.',
        'null': 'This field may not be null.'
    }
    initial = None

    def __init__(self, required=False, help_text=None, default=empty, initial=empty,
                 source=None, validators=None, error_messages=None, allow_null=False):
        self.required = required
        self.help_text = help_text
        self.default = default
        self.initial = self.initial if (initial is empty) else initial
        self.source = source
        self.field_name = None
        self.parent = None
        if validators is not None:
            self.validators = list(validators)
        self.allow_null = allow_null
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages = messages

    def bind(self, field_name, parent):
        """
        my_field = serializer.CharField(source='my_field')
        """
        assert self.source != field_name, (
            "It is redundant to specify `source='%s'` on field '%s' in "
            "serializer '%s', because it is the same as the field name. "
            "Remove the `source` keyword argument." %
            (field_name, self.__class__.__name__, parent.__class__.__name__)
        )

        self.field_name = field_name
        self.parent = parent

        if self.source is None:
            self.source = field_name

        self.source_attrs = [] if self.source == '*' else self.source.split('.')

    def get_value(self, dictionary):
        if isinstance(dictionary, Mapping):
            value = dictionary.get(self.field_name, empty)
        else:
            value = getattr(dictionary, self.field_name, empty)
        return value

    @property
    def validators(self):
        if not hasattr(self, '_validators'):
            self._validators = self.get_validators()
        return self._validators

    @validators.setter
    def validators(self, validators):
        self._validators = validators

    def get_validators(self):
        return list(self.default_validators)

    def get_attribute(self, instance):
        try:
            return get_attribute(instance, self.source_attrs)
        except (KeyError, AttributeError) as exc:
            if self.default is not empty:
                return self.get_default()
            if self.allow_null:
                return None
            if not self.required:
                raise SkipFieldException()

            msg = (
                'Got {exc_type} when attempting to get a value for field '
                '`{field}` on serializer `{serializer}`.\nThe serializer '
                'field might be named incorrectly and not match '
                'any attribute or key on the `{instance}` instance.\n'
                'Original exception text was: {exc}.'.format(
                    exc_type=type(exc).__name__,
                    field=self.field_name,
                    serializer=self.parent.__class__.__name__,
                    instance=instance.__class__.__name__,
                    exc=exc
                )
            )

            raise type(exc)(msg)

    def get_default(self):
        if self.default is empty or getattr(self.root, 'partial', False):
            raise SkipFieldException()

        if callable(self.default):
            if hasattr(self.default, 'set_context'):
                self.default.set_context(self)
            return self.default()
        return self.default

    def get_initial(self):
        if callable(self.initial):
            return self.initial()
        return self.initial

    def fail(self, key, **kwargs):
        msg = self.error_messages.get(key, 'Invalid Argument')
        message_string = msg.format(**kwargs)
        raise ValidationError(message_string)

    def validate_empty_values(self, data):
        if data is empty:
            if getattr(self.root, 'partial', False):
                raise SkipFieldException()

            if self.required:
                self.fail('required')
            return True, self.get_default()

        if data is None:
            if not self.allow_null:
                self.fail('null')

            elif self.source == '*':
                return False, None
            return True, None

        return False, data

    def run_validation(self, data=empty):
        is_empty_value, data = self.validate_empty_values(data)
        if is_empty_value:
            return data

        value = self.to_internal_value(data)
        self.run_validators(value)
        return value

    def run_validators(self, value):
        errors = []
        for validator in self.validators:
            if hasattr(validator, 'set_context'):
                validator.set_context(self)

            try:
                validator(value)
            except ValidationError as exc:
                errors.append(exc.details)
        if errors:
            raise ValidationError(errors)

    @property
    def root(self):
        root = self
        while root.parent is not None:
            root = root.parent
        return root

    def to_internal_value(self, data):
        raise NotImplementedError()

    def to_representation(self, value):
        raise NotImplementedError()

    def __new__(cls, *args, **kwargs):
        instance = super(Field, cls).__new__(cls)
        instance._args = args
        instance._kwargs = kwargs
        return instance


class BooleanField(Field):
    default_error_messages = {
        'invalid': 'Must be a valid boolean.'
    }
    initial = False
    TRUE_VALUES = {
        't', 'T',
        'y', 'Y', 'yes', 'YES',
        'true', 'True', 'TRUE',
        'on', 'On', 'ON',
        '1', 1,
        True
    }
    FALSE_VALUES = {
        'f', 'F',
        'n', 'N', 'no', 'NO',
        'false', 'False', 'FALSE',
        'off', 'Off', 'OFF',
        '0', 0, 0.0,
        False
    }

    NULL_VALUES = {'null', 'Null', 'NULL', '', None}

    def to_internal_value(self, data):
        try:
            if data in self.TRUE_VALUES:
                return True
            elif data in self.FALSE_VALUES:
                return False
            elif data in self.NULL_VALUES and self.allow_null:
                return None
        except TypeError:
            pass
        self.fail('invalid')

    def to_representation(self, value):
        if value in self.TRUE_VALUES:
            return True
        elif value in self.FALSE_VALUES:
            return False
        if value in self.NULL_VALUES and self.allow_null:
            return None
        return bool(value)


class NullBooleanField(Field):
    default_error_messages = {
        'invalid': 'Must be a valid boolean.'
    }
    initial = None
    TRUE_VALUES = {'t', 'T', 'true', 'True', 'TRUE', '1', 1, True}
    FALSE_VALUES = {'f', 'F', 'false', 'False', 'FALSE', '0', 0, 0.0, False}
    NULL_VALUES = {'n', 'N', 'null', 'Null', 'NULL', '', None}

    def __init__(self, **kwargs):
        kwargs['allow_null'] = True
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        try:
            if data in self.TRUE_VALUES:
                return True
            elif data in self.FALSE_VALUES:
                return False
            elif data in self.NULL_VALUES:
                return None
        except TypeError:
            pass
        self.fail('invalid')

    def to_representation(self, value):
        if value in self.NULL_VALUES:
            return None
        if value in self.TRUE_VALUES:
            return True
        elif value in self.FALSE_VALUES:
            return False
        return bool(value)


class CharField(Field):
    default_error_messages = {
        'invalid': 'Not a valid string.',
        'blank': 'This field may not be blank.',
    }
    initial = ''

    def __init__(self, **kwargs):
        self.allow_blank = kwargs.pop('allow_blank', False)
        self.trim_whitespace = kwargs.pop('trim_whitespace', True)
        self.max_length = kwargs.pop('max_length', None)
        self.min_length = kwargs.pop('min_length', None)
        super(CharField, self).__init__(**kwargs)

        if self.min_length is not None:
            self.validators.append(MinLengthValidator(int(self.min_length)))
        if self.max_length is not None:
            self.validators.append(MaxLengthValidator(int(self.max_length)))

    def run_validation(self, data=empty):
        if data == '' or (self.trim_whitespace and str(data).strip() == ''):
            if not self.allow_blank:
                self.fail('blank')
            return ''
        return super().run_validation(data)

    def to_internal_value(self, data):
        if isinstance(data, bool) or not isinstance(data, (str, int, float,)):
            self.fail('invalid')
        value = str(data)
        return value.strip() if self.trim_whitespace else value

    def to_representation(self, value):
        value = str(value)
        return value.strip() if self.trim_whitespace else value


class IntegerField(Field):
    default_error_messages = {
        'invalid': 'A valid integer is required.',
        'max_string_length': 'String value too large.'
    }
    MAX_STRING_LENGTH = 1000
    re_decimal = re.compile(r'\.0*\s*$')  # allow e.g. '1.0' as an int, but not '1.2'

    def __init__(self, **kwargs):
        self.max_value = kwargs.pop('max_value', None)
        self.min_value = kwargs.pop('min_value', None)
        super().__init__(**kwargs)
        if self.max_value is not None:
            self.validators.append(MaxValueValidator(self.max_value))
        if self.min_value is not None:
            self.validators.append(MinValueValidator(self.min_value))

    def to_internal_value(self, data):
        if isinstance(data, str) and len(data) > self.MAX_STRING_LENGTH:
            self.fail('max_string_length')

        try:
            data = int(self.re_decimal.sub('', str(data)))
        except (ValueError, TypeError):
            self.fail('invalid')
        return data

    def to_representation(self, value):
        return int(value)


class FloatField(Field):
    default_error_messages = {
        'invalid': 'A valid integer is required.',
        'max_string_length': 'String value too large.'
    }
    MAX_STRING_LENGTH = 1000

    def __init__(self, **kwargs):
        self.max_value = kwargs.pop('max_value', None)
        self.min_value = kwargs.pop('min_value', None)
        super().__init__(**kwargs)
        if self.max_value is not None:
            self.validators.append(MaxValueValidator(self.max_value))
        if self.min_value is not None:
            self.validators.append(MinValueValidator(self.min_value))

    def to_internal_value(self, data):
        if isinstance(data, str) and len(data) > self.MAX_STRING_LENGTH:
            self.fail('max_string_length')

        try:
            return float(data)
        except (TypeError, ValueError):
            self.fail('invalid')

    def to_representation(self, value):
        return float(value)


class BaseTimeField(Field):

    def __init__(self, output_format, to_tz="Asia/Shanghai", from_tz="UTC", *args, **kwargs):
        super(BaseTimeField, self).__init__(*args, **kwargs)
        self.output_format = output_format
        self.to_tz = to_tz
        self.from_tz = from_tz

    def to_internal_value(self, data):
        if data is None:
            return data

        if isinstance(data, str):
            data = pendulum.parse(data, tz=self.from_tz)

        if not isinstance(data, datetime.datetime):
            raise ValueError('datetime instance required')
        if data.utcoffset() is None:
            raise ValueError('timezone aware datetime required')
        if isinstance(data, pendulum.DateTime):
            data = datetime.datetime.fromtimestamp(data.timestamp(), tz=data.timezone)
        return data.astimezone(datetime.timezone.utc)

    def to_representation(self, value):

        if not value:
            return None

        if self.output_format is None:
            return value

        if isinstance(value, str):
            value = pendulum.parse(value, tz=self.from_tz)

        if isinstance(value, datetime.datetime):
            value = pendulum.instance(value, tz=self.from_tz)

        return value.in_tz(tz=self.to_tz).format(self.output_format)


class DateTimeField(BaseTimeField):
    def __init__(self, output_format="YYYY-MM-DD HH:mm:ss", *args, **kwargs):
        super(DateTimeField, self).__init__(output_format, *args, **kwargs)


class DateField(BaseTimeField):
    def __init__(self, output_format="YYYY-MM-DD", *args, **kwargs):
        super(DateField, self).__init__(output_format, *args, **kwargs)


class TimeField(BaseTimeField):
    def __init__(self, output_format="HH:mm:ss", *args, **kwargs):
        super(TimeField, self).__init__(output_format, *args, **kwargs)


class ChoiceField(Field):
    default_error_messages = {
        'invalid_choice': '"{input}" is not a valid choice.'
    }

    def __init__(self, choices, **kwargs):
        self.choices = choices
        self.allow_blank = kwargs.pop('allow_blank', False)

        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if data == '' and self.allow_blank:
            return ''

        try:
            return self.choice_strings_to_values[str(data)]
        except KeyError:
            self.fail('invalid_choice', input=data)

    def to_representation(self, value):
        if value in ('', None):
            return value
        return self.choice_strings_to_values.get(str(value), value)

    def _get_choices(self):
        return self._choices

    def _set_choices(self, choices):
        self.grouped_choices = to_choices_dict(choices)
        self._choices = flatten_choices_dict(self.grouped_choices)
        self.choice_strings_to_values = {str(key): key for key in self.choices}

    choices = property(_get_choices, _set_choices)


class _UnvalidatedField(Field):
    def __init__(self, *args, **kwargs):
        super(_UnvalidatedField, self).__init__(*args, **kwargs)
        self.allow_blank = True
        self.allow_null = True

    def to_internal_value(self, data):
        return data

    def to_representation(self, value):
        return value


class ListField(Field):
    initial = []
    child = _UnvalidatedField()
    default_error_messages = {
        'not_a_list': 'Expected a list of items but got type "{input_type}".',
        'empty': 'This list may not be empty.',
    }

    def __init__(self, *args, **kwargs):
        self.child = kwargs.pop('child', copy.deepcopy(self.child))
        self.allow_empty = kwargs.pop('allow_empty', True)
        self.max_length = kwargs.pop('max_length', None)
        self.min_length = kwargs.pop('min_length', None)
        self.child.source = None
        super().__init__(*args, **kwargs)
        self.child.bind(field_name='', parent=self)
        if self.max_length is not None:
            self.validators.append(MaxLengthValidator(self.max_length))
        if self.min_length is not None:
            self.validators.append(MinLengthValidator(self.min_length))

    def to_internal_value(self, data):
        if isinstance(data, (str, Mapping)) or not hasattr(data, '__iter__'):
            self.fail('not_a_list', input_type=type(data).__name__)
        if not self.allow_empty and len(data) == 0:
            self.fail('empty')
        return self.run_child_validation(data)

    def to_representation(self, data):
        return [self.child.to_representation(item) if item is not None else None for item in data]

    def run_child_validation(self, data):
        result = []
        errors = OrderedDict()

        for idx, item in enumerate(data):
            try:
                result.append(self.child.run_validation(item))
            except ValidationError as e:
                errors[idx] = e.details

        if not errors:
            return result

        raise ValidationError(errors)


class SerializerMethodField(Field):
    """
    class ExampleSerializer(self):
        extra_info = SerializerMethodField()
        my_field = serializer.SerializerMethodField(method_name='get_my_field')

        def get_extra_info(self, obj):
            return ...

        def get_my_field(self, obj):
            return ..

    """
    def __init__(self, method_name=None, **kwargs):
        self.method_name = method_name
        kwargs['source'] = '*'
        super(SerializerMethodField, self).__init__(**kwargs)

    def bind(self, field_name, parent):
        default_method_name = 'get_{field_name}'.format(field_name=field_name)
        assert self.method_name != default_method_name, (
            "It is redundant to specify `%s` on SerializerMethodField '%s' in "
            "serializer '%s', because it is the same as the default method name. "
            "Remove the `method_name` argument." %
            (self.method_name, field_name, parent.__class__.__name__)
        )

        if self.method_name is None:
            self.method_name = default_method_name

        super(SerializerMethodField, self).bind(field_name, parent)

    def to_internal_value(self, data):
        method = getattr(self.parent, self.method_name)
        return method(data)

    def to_representation(self, value):
        method = getattr(self.parent, self.method_name)
        return method(value)
