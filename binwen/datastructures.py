from itertools import repeat


def is_immutable(self):
    raise TypeError('%r objects are immutable' % self.__class__.__name__)


class ImmutableDict(dict):
    """
    不可变的字典
    一旦初始化成功，不再可以进行字典的变更操作
    import datastructures
    import copy

    data = {'foo': 1, 'bar': 2, 'baz': 3}

    # 实例化
    d1 = datastructures.ImmutableDict(data)
    assert sorted(d1.keys()) == ['bar', 'baz', 'foo']
    assert d1['foo'] == 1

    d2 = d1.copy()
    assert d2['foo'] == 1
    assert type(d2) == dict

    d3 = copy.copy(d1)
    assert d2['foo'] == 1
    assert type(d3) == datastructures.ImmutableDict

    d4 = datastructures.ImmutableDict.fromkeys(data.keys(), 'OK')
    assert sorted(d4.keys()) == ['bar', 'baz', 'foo']
    assert d4['foo'] == 'OK'
    assert type(d4) == datastructures.ImmutableDict

    d1.clear()
    >> raise TypeError

    d1.pop('bar')
    >> raise TypeError

    d['a'] = 1
    >> raise TypeError

    """
    _hash_cache = None

    @classmethod
    def fromkeys(cls, keys, value=None):
        return cls(zip(keys, repeat(value)))

    def __reduce_ex__(self, protocol):
        return type(self), (dict(self),)

    def __hash__(self):
        if self._hash_cache is not None:
            return self._hash_cache
        rv = self._hash_cache = hash(frozenset(self.items()))
        return rv

    def setdefault(self, key, default=None):
        is_immutable(self)

    def update(self, *args, **kwargs):
        is_immutable(self)

    def pop(self, key, default=None):
        is_immutable(self)

    def popitem(self):
        is_immutable(self)

    def __setitem__(self, key, value):
        is_immutable(self)

    def __delitem__(self, key):
        is_immutable(self)

    def clear(self):
        is_immutable(self)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, dict.__repr__(self))

    def copy(self):
        return dict(self)

    def __copy__(self):
        return self


class ConstantsObject(ImmutableDict):
    """
    根据dict初始化对象，dict的 key value 会被转化为object的 attribute。初始化成功后不可以再更改 attribute
    data = {'foo': 1, 'bar': 2, 'baz': 3}
    d = datatypes.ConstantsObject(data)
    assert d.foo == 1

    d.foo = 2
    >> raise TypeError
    """

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value

    def __dir__(self):
        return self.keys()
