import inspect
import logging
import os.path

from binwen import exceptions
from binwen.config import Config, ConfigAttribute, DEFAULT_CONFIG
from binwen.datastructures import ConstantsObject
from binwen.utils.functional import import_obj
from binwen.utils.cache import cached_property
from binwen.utils.log import has_level_handler


class BaseApp:
    config_class = Config
    debug = ConfigAttribute('DEBUG')
    testing = ConfigAttribute('TESTING')
    tz = ConfigAttribute('TIMEZONE')

    def __init__(self, root_path, env):
        if not os.path.isabs(root_path):
            root_path = os.path.abspath(root_path)

        self.root_path = root_path
        self.name = os.path.basename(root_path)
        self.env = env
        self.config = self.make_config()
        self._servicers = {}
        self._extensions = {}
        self._middlewares = []

    def make_config(self) -> Config:
        config = self.config_class(DEFAULT_CONFIG)
        return config

    @cached_property
    def logger(self):
        logger = logging.getLogger('binwen.app')
        if self.debug and logger.level == logging.NOTSET:
            logger.setLevel(logging.DEBUG)

        if not has_level_handler(logger):
            default_handler = logging.StreamHandler()
            default_handler.setFormatter(logging.Formatter(
                '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
            ))
            logger.addHandler(default_handler)

        return logger

    @cached_property
    def servicers(self):
        rv = ConstantsObject(self._servicers)
        del self._servicers
        return rv

    @cached_property
    def extensions(self):
        rv = ConstantsObject(self._extensions)
        del self._extensions
        return rv

    @cached_property
    def middlewares(self):
        rv = tuple(self._middlewares)
        del self._middlewares
        return rv

    def _register_servicer(self, servicer):
        name = servicer.__name__
        if name in self._servicers:
            raise exceptions.ConfigException(f'servicer duplicated: {name}')

        add_func = self._get_servicer_add_func(servicer)
        self._servicers[name] = (add_func, servicer)

    @staticmethod
    def _get_servicer_add_func(servicer):
        for b in servicer.__bases__:
            if b.__name__.endswith('Servicer'):
                m = inspect.getmodule(b)
                return getattr(m, f'add_{b.__name__}_to_server')

    def _register_extension(self, name, ext):
        ext.init_app(self)
        if name in self._extensions:
            raise exceptions.ConfigException(f'extension duplicated: {name}')
        self._extensions[name] = ext

    def load_middleware(self):
        middleware = ['binwen.middleware.GuardMiddleware'] + self.config["MIDDLEWARE"]
        for mn in middleware:
            m = import_obj(mn)
            self._middlewares.insert(0, m)
        return self.middlewares

    def load_extensions_in_module(self, module):
        def is_ext(ins):
            return not inspect.isclass(ins) and hasattr(ins, 'init_app')

        for n, ext in inspect.getmembers(module, is_ext):
            self._register_extension(n, ext)

        return self.extensions

    def load_servicers_in_app(self):
        for app in self.config["INSTALLED_APPS"]:
            app_module = import_obj(f"{app}.servicers")

            for _, _servicer in inspect.getmembers(app_module, inspect.isclass):
                if getattr(_servicer, "__isbwservicercls__", False):
                    self._register_servicer(_servicer)

        return self.servicers

    def ready(self):
        pass
