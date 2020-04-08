import base64
import binascii
import functools
import hashlib
import hmac
import importlib
import warnings

from binwen import current_app
from binwen.exceptions import ImproperlyConfigured
from binwen.utils.crypto import pbkdf2
from binwen.utils.encoding import to_bytes
from binwen.utils.functional import get_random_string, import_obj

UNUSABLE_PASSWORD_PREFIX = '!'
UNUSABLE_PASSWORD_SUFFIX_LENGTH = 40


def is_password_usable(encoded):
    return encoded is None or not encoded.startswith(UNUSABLE_PASSWORD_PREFIX)


def check_password(password, encoded, resetter=None, preferred='default'):
    """
    当加密方式与preferred的不一样时，可以通过resetter处理
    """
    if password is None or not is_password_usable(encoded):
        return False

    preferred = get_hasher(preferred)
    try:
        hasher = identify_hasher(encoded)
    except ValueError:
        return False

    hasher_changed = hasher.algorithm != preferred.algorithm
    must_update = hasher_changed or preferred.must_update(encoded)
    is_correct = hasher.verify(password, encoded)

    if not is_correct and not hasher_changed and must_update:
        hasher.harden_runtime(password, encoded)

    if resetter and is_correct and must_update:
        resetter(password)

    return is_correct


def make_password(password, salt=None, preferred='default'):
    if password is None:
        return UNUSABLE_PASSWORD_PREFIX + get_random_string(UNUSABLE_PASSWORD_SUFFIX_LENGTH)

    hasher = get_hasher(preferred)
    salt = salt or hasher.salt()
    return hasher.encode(password, salt)


@functools.lru_cache()
def get_hashers():
    hashers = []
    for hasher_path in current_app.config["PASSWORD_HASHERS"]:
        hasher = import_obj(hasher_path)()
        if not getattr(hasher, 'algorithm'):
            raise ImproperlyConfigured(f"hasher doesn't specify an algorithm name: {hasher_path}")
        hashers.append(hasher)
    return hashers


@functools.lru_cache()
def get_hashers_by_algorithm():
    return {hasher.algorithm: hasher for hasher in get_hashers()}


def get_hasher(algorithm='default'):
    if hasattr(algorithm, 'algorithm'):
        return algorithm

    elif algorithm == 'default':
        return get_hashers()[0]

    else:
        hashers = get_hashers_by_algorithm()
        try:
            return hashers[algorithm]
        except KeyError:
            raise ValueError(f"Unknown password hashing algorithm '{algorithm}'. "
                             f"Did you specify it in the PASSWORD_HASHERS config?")


def identify_hasher(encoded):
    if (len(encoded) == 32 and '$' not in encoded) or (len(encoded) == 37 and encoded.startswith('md5$$')):
        algorithm = 'unsalted_md5'
    elif len(encoded) == 46 and encoded.startswith('sha1$$'):
        algorithm = 'unsalted_sha1'
    else:
        algorithm = encoded.split('$', 1)[0]

    return get_hasher(algorithm)


def constant_time_compare(val1, val2):
    return hmac.compare_digest(to_bytes(val1), to_bytes(val2))


class BasePasswordHasher:
    algorithm = None
    library = None

    def _load_library(self):
        if self.library is not None:
            if isinstance(self.library, (tuple, list)):
                name, mod_path = self.library
            else:
                mod_path = self.library
            try:
                module = importlib.import_module(mod_path)
            except ImportError as e:
                raise ValueError(f"Couldn't load {self.__class__.__name__} algorithm library:{e}")

            return module
        raise ValueError(f"Hasher {self.__class__.__name__} doesn't specify a library attribute")

    def salt(self):
        return get_random_string()

    def verify(self, password, encoded):
        raise NotImplementedError('subclasses of BasePasswordHasher must provide a verify() method')

    def encode(self, password, salt):
        raise NotImplementedError('subclasses of BasePasswordHasher must provide an encode() method')

    def must_update(self, encoded):
        return False

    def harden_runtime(self, password, encoded):
        warnings.warn('subclasses of BasePasswordHasher should provide a harden_runtime() method')


class PBKDF2PasswordHasher(BasePasswordHasher):
    """
    使用PBKDF2算法进行安全密码哈希(推荐)
    配置为使用PBKDF2 + HMAC + SHA256。
    结果是一个64字节的二进制字符串,迭代可能会改变;但如果更改SHA256，则必须重命名算法。
    """
    algorithm = "pbkdf2_sha256"
    iterations = 150000
    digest = hashlib.sha256

    def encode(self, password, salt, iterations=None):
        assert password is not None
        assert salt and '$' not in salt
        iterations = iterations or self.iterations
        password_hash = pbkdf2(password, salt, iterations, digest=self.digest)
        password_hash = base64.b64encode(password_hash).decode('ascii').strip()
        return "%s$%d$%s$%s" % (self.algorithm, iterations, salt, password_hash)

    def verify(self, password, encoded):
        algorithm, iterations, salt, pwd_hash = encoded.split('$', 3)
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, salt, int(iterations))
        return constant_time_compare(encoded, encoded_2)

    def must_update(self, encoded):
        iterations = encoded.split('$', 3)[1]
        return int(iterations) != self.iterations

    def harden_runtime(self, password, encoded):
        algorithm, iterations, salt, pwd_hash = encoded.split('$', 3)
        extra_iterations = self.iterations - int(iterations)
        if extra_iterations > 0:
            self.encode(password, salt, extra_iterations)


class PBKDF2SHA1PasswordHasher(PBKDF2PasswordHasher):
    algorithm = "pbkdf2_sha1"
    digest = hashlib.sha1


class Argon2PasswordHasher(BasePasswordHasher):
    """
    使用argon2算法进行安全密码哈希。
    这是2013-2015年密码哈希大赛的冠军
    (https://password-hashing.net)。它需要argon2-cffi库依赖于本机C代码，可能会导致可移植性问题。
    """
    algorithm = 'argon2'
    library = 'argon2'

    time_cost = 2
    memory_cost = 512
    parallelism = 2

    def encode(self, password, salt):
        argon2 = self._load_library()
        data = argon2.low_level.hash_secret(
            password.encode(),
            salt.encode(),
            time_cost=self.time_cost,
            memory_cost=self.memory_cost,
            parallelism=self.parallelism,
            hash_len=argon2.DEFAULT_HASH_LENGTH,
            type=argon2.low_level.Type.I,
        )
        return self.algorithm + data.decode('ascii')

    def verify(self, password, encoded):
        argon2 = self._load_library()
        algorithm, rest = encoded.split('$', 1)
        assert algorithm == self.algorithm
        try:
            return argon2.low_level.verify_secret(
                ('$' + rest).encode('ascii'),
                password.encode(),
                type=argon2.low_level.Type.I,
            )
        except argon2.exceptions.VerificationError:
            return False

    def must_update(self, encoded):
        (algorithm, variety, version, time_cost, memory_cost, parallelism,
            salt, data) = self._decode(encoded)
        assert algorithm == self.algorithm
        argon2 = self._load_library()
        return (
            argon2.low_level.ARGON2_VERSION != version or
            self.time_cost != time_cost or
            self.memory_cost != memory_cost or
            self.parallelism != parallelism
        )

    def harden_runtime(self, password, encoded):
        pass

    def _decode(self, encoded):
        """
        Split an encoded hash and return: (
            algorithm, variety, version, time_cost, memory_cost,
            parallelism, salt, data,
        ).
        """
        bits = encoded.split('$')
        if len(bits) == 5:
            # Argon2 < 1.3
            algorithm, variety, raw_params, salt, data = bits
            version = 0x10
        else:
            assert len(bits) == 6
            algorithm, variety, raw_version, raw_params, salt, data = bits
            assert raw_version.startswith('v=')
            version = int(raw_version[len('v='):])
        params = dict(bit.split('=', 1) for bit in raw_params.split(','))
        assert len(params) == 3 and all(x in params for x in ('t', 'm', 'p'))
        time_cost = int(params['t'])
        memory_cost = int(params['m'])
        parallelism = int(params['p'])
        return (
            algorithm, variety, version, time_cost, memory_cost, parallelism,
            salt, data,
        )


class BCryptSHA256PasswordHasher(BasePasswordHasher):
    """
    Secure password hashing using the bcrypt algorithm (recommended)

    This is considered by many to be the most secure algorithm but you
    must first install the bcrypt library.  Please be warned that
    this library depends on native C code and might cause portability
    issues.
    """
    algorithm = "bcrypt_sha256"
    digest = hashlib.sha256
    library = ("bcrypt", "bcrypt")
    rounds = 12

    def salt(self):
        bcrypt = self._load_library()
        return bcrypt.gensalt(self.rounds)

    def encode(self, password, salt):
        bcrypt = self._load_library()
        password = password.encode()
        # Hash the password prior to using bcrypt to prevent password
        # truncation as described in #20138.
        if self.digest is not None:
            # Use binascii.hexlify() because a hex encoded bytestring is str.
            password = binascii.hexlify(self.digest(password).digest())

        data = bcrypt.hashpw(password, salt)
        return "%s$%s" % (self.algorithm, data.decode('ascii'))

    def verify(self, password, encoded):
        algorithm, data = encoded.split('$', 1)
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, data.encode('ascii'))
        return constant_time_compare(encoded, encoded_2)

    def must_update(self, encoded):
        algorithm, empty, algostr, rounds, data = encoded.split('$', 4)
        return int(rounds) != self.rounds

    def harden_runtime(self, password, encoded):
        _, data = encoded.split('$', 1)
        salt = data[:29]  # Length of the salt in bcrypt.
        rounds = data.split('$')[2]
        # work factor is logarithmic, adding one doubles the load.
        diff = 2**(self.rounds - int(rounds)) - 1
        while diff > 0:
            self.encode(password, salt.encode('ascii'))
            diff -= 1


class BCryptPasswordHasher(BCryptSHA256PasswordHasher):
    """
    Secure password hashing using the bcrypt algorithm

    This is considered by many to be the most secure algorithm but you
    must first install the bcrypt library.  Please be warned that
    this library depends on native C code and might cause portability
    issues.

    This hasher does not first hash the password which means it is subject to
    bcrypt's 72 bytes password truncation. Most use cases should prefer the
    BCryptSHA256PasswordHasher.
    """
    algorithm = "bcrypt"
    digest = None


class SHA1PasswordHasher(BasePasswordHasher):
    """
    The SHA1 password hashing algorithm (not recommended)
    """
    algorithm = "sha1"

    def encode(self, password, salt):
        assert password is not None
        assert salt and '$' not in salt
        hash = hashlib.sha1((salt + password).encode()).hexdigest()
        return "%s$%s$%s" % (self.algorithm, salt, hash)

    def verify(self, password, encoded):
        algorithm, salt, hash = encoded.split('$', 2)
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, salt)
        return constant_time_compare(encoded, encoded_2)

    def harden_runtime(self, password, encoded):
        pass


class MD5PasswordHasher(BasePasswordHasher):
    """
    The Salted MD5 password hashing algorithm (not recommended)
    """
    algorithm = "md5"

    def encode(self, password, salt):
        assert password is not None
        assert salt and '$' not in salt
        hash = hashlib.md5((salt + password).encode()).hexdigest()
        return "%s$%s$%s" % (self.algorithm, salt, hash)

    def verify(self, password, encoded):
        algorithm, salt, hash = encoded.split('$', 2)
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, salt)
        return constant_time_compare(encoded, encoded_2)

    def harden_runtime(self, password, encoded):
        pass


class UnsaltedSHA1PasswordHasher(BasePasswordHasher):
    """
    Very insecure algorithm that you should *never* use; store SHA1 hashes
    with an empty salt.

    This class is implemented because Django used to accept such password
    hashes. Some older Django installs still have these values lingering
    around so we need to handle and upgrade them properly.
    """
    algorithm = "unsalted_sha1"

    def salt(self):
        return ''

    def encode(self, password, salt):
        assert salt == ''
        hash = hashlib.sha1(password.encode()).hexdigest()
        return 'sha1$$%s' % hash

    def verify(self, password, encoded):
        encoded_2 = self.encode(password, '')
        return constant_time_compare(encoded, encoded_2)

    def harden_runtime(self, password, encoded):
        pass


class UnsaltedMD5PasswordHasher(BasePasswordHasher):
    """
    Incredibly insecure algorithm that you should *never* use; stores unsalted
    MD5 hashes without the algorithm prefix, also accepts MD5 hashes with an
    empty salt.

    This class is implemented because Django used to store passwords this way
    and to accept such password hashes. Some older Django installs still have
    these values lingering around so we need to handle and upgrade them
    properly.
    """
    algorithm = "unsalted_md5"

    def salt(self):
        return ''

    def encode(self, password, salt):
        assert salt == ''
        return hashlib.md5(password.encode()).hexdigest()

    def verify(self, password, encoded):
        if len(encoded) == 37 and encoded.startswith('md5$$'):
            encoded = encoded[5:]
        encoded_2 = self.encode(password, '')
        return constant_time_compare(encoded, encoded_2)

    def harden_runtime(self, password, encoded):
        pass


class CryptPasswordHasher(BasePasswordHasher):
    """
    Password hashing using UNIX crypt (not recommended)

    The crypt module is not supported on all platforms.
    """
    algorithm = "crypt"
    library = "crypt"

    def salt(self):
        return get_random_string(2)

    def encode(self, password, salt):
        crypt = self._load_library()
        assert len(salt) == 2
        data = crypt.crypt(password, salt)
        assert data is not None  # A platform like OpenBSD with a dummy crypt module.
        # we don't need to store the salt, but Django used to do this
        return "%s$%s$%s" % (self.algorithm, '', data)

    def verify(self, password, encoded):
        crypt = self._load_library()
        algorithm, salt, data = encoded.split('$', 2)
        assert algorithm == self.algorithm
        return constant_time_compare(data, crypt.crypt(password, data))

    def harden_runtime(self, password, encoded):
        pass
