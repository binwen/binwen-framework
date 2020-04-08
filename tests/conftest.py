import os
import logging
from io import StringIO
import pytest

import binwen
from binwen.test.fixtures import *  # noqa


@pytest.fixture
def log_stream():
    return StringIO()


@pytest.fixture
def app(log_stream):
    os.environ.setdefault('BINWEN_ENV', 'test')
    logger = logging.getLogger('binwen')
    h = logging.StreamHandler(log_stream)
    logger.addHandler(h)
    root = os.path.join(os.path.dirname(__file__), 'demo')
    app = binwen.create_app(root)
    yield app
    logger.removeHandler(h)
    binwen.globals._app = None
