import sys
import logging
from unittest import mock

import pytest

from binwen import app, exceptions


def test_baseapp(caplog):
    root_path = './tests/demo'
    sys.path.append(root_path)
    _app = app.BaseApp(root_path, env='test')
    assert not _app.debug

    from .demo.config import test

    _app.config.from_object(test)
    assert _app.debug
    _app.load_middleware()

    assert len(_app.middlewares) == 3

    with mock.patch('binwen.globals._app', new=_app):
        import extensions
        from helloworld import servicers


    with pytest.raises(exceptions.ConfigException):
        _app._register_servicer(servicers.GreeterServicer)
        _app._register_servicer(servicers.GreeterServicer)

    _app._servicers = {}
    _app.load_servicers_in_app()
    assert 'GreeterServicer' in _app.servicers
    servicer = _app.servicers['GreeterServicer']
    assert isinstance(servicer, tuple)
    assert servicer == (
        servicers.helloworld_pb2_grpc.add_GreeterServicer_to_server,
        servicers.GreeterServicer)

    with pytest.raises(exceptions.ConfigException):
        _app._register_extension('celeryapp', extensions.celeryapp)
        _app._register_extension('celeryapp', extensions.celeryapp)
    _app._extensions = {}
    _app.load_extensions_in_module(extensions)
    ext = _app.extensions.celeryapp
    assert ext is extensions.celeryapp

    with caplog.at_level(logging.DEBUG):
        _app.logger.debug('test')
        assert caplog.text
