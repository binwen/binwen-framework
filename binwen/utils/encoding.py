import uuid
import json
import decimal
import datetime
from decimal import Decimal
try:
    import ujson as jsonlib
    has_ujson = True
except ImportError:
    jsonlib = json
    has_ujson = False

_PROTECTED_TYPES = (int, type(None), float, Decimal, datetime.datetime, datetime.date, datetime.time)


def is_aware(value):
    return value.utcoffset() is not None


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            representation = obj.isoformat()
            if representation.endswith('+00:00'):
                representation = representation[:-6] + 'Z'
            return representation
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.time):
            if is_aware(obj):
                raise ValueError("JSON can't represent timezone-aware times.")
            representation = obj.isoformat()
            return representation
        elif isinstance(obj, datetime.timedelta):
            return str(obj.total_seconds())
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, bytes):
            return obj.decode('utf-8')
        elif hasattr(obj, 'tolist'):
            return obj.tolist()
        elif hasattr(obj, '__getitem__'):
            try:
                return dict(obj)
            except Exception:
                pass
        elif hasattr(obj, '__iter__'):
            return tuple(item for item in obj)

        return super(JSONEncoder, self).default(obj)


def json_encode(value, indent=None, sort_keys=False):
    if not has_ujson:
        options = {
            "ensure_ascii": False,
            "allow_nan": False,
            "indent": indent,
            "separators": (",", ":"),
            "cls": JSONEncoder,
            "sort_keys": sort_keys
        }
        return jsonlib.dumps(value, **options)

    return jsonlib.dumps(value, escape_forward_slashes=False)


def json_decode(value):
    return jsonlib.loads(value)


def is_protected_type(obj):

    return isinstance(obj, _PROTECTED_TYPES)


def to_text(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    转字符串
    """
    if issubclass(type(s), str):
        return s

    if strings_only and is_protected_type(s):
        return s

    try:
        if not issubclass(type(s), str):
            s = str(s, encoding, errors) if isinstance(s, bytes) else str(s)
        else:
            s = s.decode(encoding, errors)
    except UnicodeDecodeError as e:
        s = ' '.join(to_text(arg, encoding, strings_only, errors) for arg in s)

    return s


def to_bytes(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    转字节
    """
    if isinstance(s, bytes):
        if encoding in ("utf-8", "utf8"):
            return s
        else:
            return s.decode('utf-8', errors).encode(encoding, errors)

    if strings_only and is_protected_type(s):
        return s

    if isinstance(s, memoryview):
        return bytes(s)

    if not isinstance(s, str):
        try:
            return str(s).encode(encoding)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                return b' '.join(to_bytes(arg, encoding, strings_only, errors) for arg in s)
            return str(s).encode(encoding, errors)
    else:
        return s.encode(encoding, errors)

