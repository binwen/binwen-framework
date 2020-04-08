from types import FunctionType
from functools import wraps

from binwen import current_app


def wrap_handler(handler):
    h = handler

    for m in current_app.middlewares:
        h = m(current_app, h, handler)

    @wraps(handler)
    def wrapped(self, request, context):
        return h(self, request, context)

    return wrapped


class ServicerMeta(type):
    def __new__(cls, name, bases, kws):
        _kws = {}
        for k, v in kws.items():
            if isinstance(v, FunctionType):
                v = wrap_handler(v)
            _kws[k] = v
        cls_obj = super().__new__(cls, name, bases, _kws)
        cls_obj.__isbwservicercls__ = True
        return cls_obj

