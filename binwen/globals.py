import os
import sys

from binwen.utils.functional import import_obj
from binwen.local import LocalProxy

_app = None


def create_app(root_path=None):
    global _app
    if _app is not None:
        return _app

    if root_path is None:
        root_path = os.getcwd()

    sys.path.append(root_path)
    env = os.environ.get('BINWEN_ENV', 'dev')
    config = import_obj('config.{}'.format(env))

    app_class = import_obj('app:App')
    _app = app_class(root_path, env=env)
    _app.config.from_object(config)

    _app.load_middleware()
    _app.load_extensions_in_module(import_obj('extensions'))
    _app.load_servicers_in_app()

    _app.ready()

    return _app


current_app = LocalProxy(lambda: _app)
