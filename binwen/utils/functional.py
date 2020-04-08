import sys
import string
import random
import hashlib
import inspect
import functools
import collections
import time
from collections import OrderedDict
from collections.abc import Mapping

try:
    random = random.SystemRandom()
    using_system_random = True
except NotImplementedError:
    using_system_random = False


def is_simple_callable(obj):
    """
    判断对象是否为可执行的对象，比如类、方法等
    """
    if not (inspect.isfunction(obj) or inspect.ismethod(obj) or isinstance(obj, functools.partial)):
        return False

    sig = inspect.signature(obj)
    params = sig.parameters.values()
    return all(
        param.kind == param.VAR_POSITIONAL or
        param.kind == param.VAR_KEYWORD or
        param.default != param.empty
        for param in params
    )


def get_attribute(instance, attributes):
    """
    获取对象的属性值
    """
    for attr in attributes:
        if instance is None:
            return None

        if isinstance(instance, collections.Mapping):
            instance = instance[attr]
        else:
            instance = getattr(instance, attr)

        if is_simple_callable(instance):
            try:
                instance = instance()
            except (AttributeError, KeyError) as exc:
                raise ValueError(f'Exception raised in callable attribute "{attr}"; original exception was: {exc}')

    return instance


def import_obj(import_name):
    """
    导入对象
    import_obj('datetime.date')
    import_obj('binwen.app:BaseApp')
    import_obj(str)
    """
    if import_name is None:
        return import_name

    elif callable(import_name):
        return import_name

    import_name = str(import_name).replace(':', '.')
    try:
        __import__(import_name)
    except ImportError:
        if '.' not in import_name:
            raise
    else:
        return sys.modules[import_name]

    module_name, obj_name = import_name.rsplit('.', 1)
    module = __import__(module_name, None, None, [obj_name])
    try:
        return getattr(module, obj_name)
    except AttributeError as e:
        raise ImportError(e)


class Singleton(type):
    """
    class A(metaclass=utils.Singleton):
       pass

    s1 = A()
    s2 = A()
    assert s1 is s2
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)

        return cls._instances[cls]


def get_random_string(length=12, allowed_chars=None):
    """
    生成对应长度的随机字符串
    """
    if allowed_chars is None:
        allowed_chars = string.digits + string.ascii_letters

    if not using_system_random:
        random.seed(hashlib.sha256(f'{random.getstate()}{time.time()}').encode()).digest()
    return ''.join(random.choice(allowed_chars) for _ in range(length))


def to_choices_dict(choices):
    """
    to_choices_dict([1]) -> {1: 1}
    to_choices_dict([(1, '1st'), (2, '2nd')]) -> {1: '1st', 2: '2nd'}
    to_choices_dict([('Group', ((1, '1st'), 2))]) -> {'Group': {1: '1st', 2: '2'}}
    """
    # Allow single, paired or grouped choices style:
    # choices = [1, 2, 3]
    # choices = [(1, 'First'), (2, 'Second'), (3, 'Third')]
    # choices = [('Category', ((1, 'First'), (2, 'Second'))), (3, 'Third')]
    ret = OrderedDict()
    for choice in choices:
        if not isinstance(choice, (list, tuple)):
            # single choice
            ret[choice] = choice
        else:
            key, value = choice
            if isinstance(value, (list, tuple)):
                # grouped choices (category, sub choices)
                ret[key] = to_choices_dict(value)
            else:
                # paired choice (key, display value)
                ret[key] = value
    return ret


def flatten_choices_dict(choices):
    """
    flatten_choices_dict({1: '1st', 2: '2nd'}) -> {1: '1st', 2: '2nd'}
    flatten_choices_dict({'Group': {1: '1st', 2: '2nd'}}) -> {1: '1st', 2: '2nd'}
    """
    ret = OrderedDict()
    for key, value in choices.items():
        if isinstance(value, dict):
            # grouped choices (category, sub choices)
            for sub_key, sub_value in value.items():
                ret[sub_key] = sub_value
        else:
            # choice (key, display value)
            ret[key] = value
    return ret
