import logging
from importlib import import_module
from typing import Any, Callable, Dict, Mapping, Optional, Union

from binwen.utils.encoding import json_decode
from binwen.datastructures import ConstantsObject, ImmutableDict

DEFAULT_CONFIG = ImmutableDict({
    'DEBUG': False,
    'TESTING': False,
    'TIMEZONE': 'UTC',
    'GRPC_LOG_LEVEL': 'WARNING',
    'GRPC_LOG_HANDLER': logging.StreamHandler(),
    'GRPC_LOG_FORMAT': '[%(asctime)s %(levelname)s in %(module)s] %(message)s',
    'GRPC_GRACE': 5,
    'MIDDLEWARES': [
        'binwen.middleware.ServiceLogMiddleware',
        'binwen.middleware.RpcErrorMiddleware',
    ],
    'INSTALLED_APPS': [],
    'PASSWORD_HASHERS': [
        "binwen.contrib.password.PBKDF2PasswordHasher",
        'binwen.contrib.password.PBKDF2SHA1PasswordHasher',
        'binwen.contrib.password.Argon2PasswordHasher',
        'binwen.contrib.password.BCryptSHA256PasswordHasher'
    ]
})


class ConfigAttribute:
    """
    class Object:
        config = {}
        foo = ConfigAttribute('foo')

    obj = Object()
    obj.foo = 'bob'
    assert obj.foo == obj.config['foo']
    """

    def __init__(self, key: str, converter: Optional[Callable] = None) -> None:
        self.key = key
        self.converter = converter

    def __get__(self, instance: object, owner: type = None) -> Any:
        if instance is None:
            return self
        result = instance.config[self.key]
        if self.converter is not None:
            return self.converter(result)
        else:
            return result

    def __set__(self, instance: object, value: Any) -> None:
        instance.config[self.key] = value


class Config(dict):

    def __init__(self, defaults: Optional[dict] = None) -> None:
        defaults = {k.upper(): v for k, v in defaults.items()} if defaults else {}

        super().__init__(defaults)

    def from_object(self, instance: Union[object, str]) -> None:
        """
        app.config.from_object('module')
        app.config.from_object('module.instance')
        from module import instance
        app.config.from_object(instance)

        """
        if isinstance(instance, str):
            try:
                path, config = instance.rsplit('.', 1)
            except ValueError:
                path = instance
                instance = import_module(path)
            else:
                module = import_module(path)
                instance = getattr(module, config)

        for key in dir(instance):
            if key.isupper():
                self[key] = getattr(instance, key)

    def from_json(self, file_path: str, silent: bool = False) -> None:
        """app.config.from_json('/etc/binwen/config.json')
        """
        try:
            with open(file_path) as file_:
                data = json_decode(file_.read())
        except (FileNotFoundError, IsADirectoryError):
            if not silent:
                raise
        else:
            self.from_mapping(data)

    def from_mapping(self, mapping: Optional[Mapping[str, Any]] = None, **kwargs: Any) -> None:
        """
        config = {'FOO': 'bar'}
        app.config.from_mapping(config)
        app.config.form_mapping(FOO='bar')
        """
        mappings: Dict[str, Any] = {}
        if mapping is not None:
            mappings.update(mapping)
        mappings.update(kwargs)
        for key, value in mappings.items():
            if key.isupper():
                self[key] = value

    def get_namespace(self, namespace: str, lowercase: bool = True, trim_namespace: bool = True) -> Dict[str, Any]:
        """
        config = {'FOO_A': 'a', 'FOO_BAR': 'bar', 'BAR': False}
        app.config.from_mapping(config)
        assert app.config.get_namespace('FOO_') == {'a': 'a', 'bar': 'bar'}
        """
        config = {}
        for key, value in self.items():
            if not key.startswith(namespace):
                continue

            if trim_namespace:
                new_key = key[len(namespace):]
            else:
                new_key = key

            if lowercase:
                new_key = new_key.lower()

            config[new_key] = value

        return ConstantsObject(config)

    def __getitem__(self, key: str) -> Any:
        return super().__getitem__(key.upper())

    def __setitem__(self, key: str, value: Any) -> None:
        return super().__setitem__(key.upper(), value)

    def __getattr__(self, item: str) -> Any:
        return super().__getitem__(item.upper())

    def __setattr__(self, key: str, value: Any) -> None:
        return super().__setitem__(key.upper(), value)

    def __contains__(self, key: str) -> bool:
        return super().__contains__(key.upper())

    def __repr__(self) -> str:
        return '<%s %s>' % (self.__class__.__name__, dict.__repr__(self))

