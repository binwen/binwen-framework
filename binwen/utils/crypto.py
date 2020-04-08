import hashlib

from binwen.utils.encoding import to_bytes

try:
    from fastpbkdf2 import pbkdf2_hmac
except ImportError:
    from hashlib import pbkdf2_hmac


def pbkdf2(password, salt, iterations, dklen=0, digest=None):
    digest = hashlib.sha256 if digest is None else digest
    dklen = dklen or None
    password = to_bytes(password)
    salt = to_bytes(salt)
    return pbkdf2_hmac(digest().name, password, salt, iterations, dklen)
