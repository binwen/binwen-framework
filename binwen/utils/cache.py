from threading import RLock


class SafeCachedProperty:
    """
    class ForTest:
        def __init__(self):
            self.count = 0

        @utils.cached_property
        def cached_count(self):
            return self.count

    ins = ForTest()
    assert ins.cached_count == 0
    ins.count = 10
    assert ins.cached_count == 0
    """
    def __init__(self, func, name=None, doc=None):
        self.func = func
        self.__doc__ = doc or getattr(func, '__doc__')
        self.name = name or func.__name__
        self.lock = RLock()

    def __get__(self, instance, cls=None):
        with self.lock:
            if instance is None:
                return self
            try:
                return instance.__dict__[self.name]
            except KeyError:
                res = instance.__dict__[self.name] = self.func(instance)
                return res


cached_property = SafeCachedProperty
