import pytest
import logging
from binwen.utils.functional import import_obj, Singleton
from binwen.utils.cache import cached_property
from binwen.utils.log import has_level_handler


class BA:
    name = None


def test_import_obj(app):
    from binwen.app import BaseApp
    import datetime
    assert import_obj('datetime.date') is datetime.date
    assert import_obj('datetime.date') is datetime.date
    assert import_obj('datetime') is datetime
    assert import_obj('binwen.app:BaseApp') is BaseApp
    from tests.demo.helloworld.servicers import GreeterServicer as GreeterServicer2
    m = import_obj(GreeterServicer2)
    from tests.demo.helloworld.servicers import GreeterServicer
    assert m is GreeterServicer
    with pytest.raises(ImportError):
        import_obj('notexist')
    with pytest.raises(ImportError):
        import_obj('datetime.XXXXXXXXXXXX')
    ba = BA()
    with pytest.raises(ImportError):
        assert ba is import_obj(ba)


def test_cached_property():
    class ForTest:

        def __init__(self):
            self.count = 0

        @cached_property
        def cached_count(self):
            return self.count

    assert isinstance(ForTest.cached_count, cached_property)
    ins = ForTest()
    assert ins.cached_count == 0
    ins.count = 10
    assert ins.cached_count == 0


def test_singleton():
    class A(metaclass=Singleton):
        pass

    s1 = A()
    s2 = A()
    assert s1 is s2


def test_has_level_handler():
    # reset root logger
    root = logging.getLogger()
    root.handlers = []
    root.filters = []
    root.setLevel(logging.ERROR)

    l1 = logging.getLogger('testapp')
    l1.setLevel(logging.ERROR)
    l2 = logging.getLogger('testapp.sub')
    l3 = logging.getLogger('testapp.nest')
    l3.propagate = False

    assert not has_level_handler(l2)
    assert not has_level_handler(l3)

    h1 = logging.StreamHandler()
    h1.setLevel('INFO')
    l1.addHandler(h1)
    assert has_level_handler(l2)
    assert not has_level_handler(l3)
    l3.setLevel(logging.ERROR)
    assert not has_level_handler(l3)

    l2.setLevel(logging.DEBUG)
    assert not has_level_handler(l2)
    h2 = logging.StreamHandler()
    h2.setLevel(logging.DEBUG)
    l2.addHandler(h2)
    assert has_level_handler(l2)

    h3 = logging.StreamHandler()
    h3.setLevel(logging.DEBUG)
    l3.addHandler(h3)
    assert has_level_handler(l3)
