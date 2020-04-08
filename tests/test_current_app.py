import os
import binwen


def test_current_app():
    assert not binwen.current_app
    os.environ.setdefault('BINWEN_ENV', 'test')
    app = binwen.create_app('./tests/wd')
    assert app == binwen.current_app
    assert binwen.create_app('./tests/wd') is app
    assert app.debug

    from tests.demo.config import test
    from helloworld.servicers import GreeterServicer, helloworld_pb2_grpc
    from extensions import celeryapp

    assert app.config.get('INSTALLED_APPS') == ["helloworld"]
    assert app.config.get('PRO_NAME') == test.PRO_NAME
    servicer = app.servicers['GreeterServicer']
    assert servicer == (helloworld_pb2_grpc.add_GreeterServicer_to_server, GreeterServicer)
    extension = app.extensions.celeryapp
    assert extension is celeryapp
