import os
import re
import socket
from urllib.parse import urlsplit, urlunsplit

from binwen.exceptions import ValidationError
from binwen.utils.encoding import to_text


class RegexValidator:
    regex = ''
    message = 'Enter a valid value'
    inverse_match = False
    flags = 0

    def __init__(self, regex=None, message=None, inverse_match=None, flags=None):
        if regex is not None:
            self.regex = regex
        if message is not None:
            self.message = message
        if inverse_match is not None:
            self.inverse_match = inverse_match
        if flags is not None:
            self.flags = flags
        if self.flags and not isinstance(self.regex, str):
            raise TypeError("If the flags are set, regex must be a regular expression string.")

        self.regex = re.compile(regex, self.flags)

    def __call__(self, value):
        if not (self.inverse_match is not bool(self.regex.search(to_text(value)))):
            raise ValidationError(self.message)


class URLValidator(RegexValidator):
    ul = '\u00a1-\uffff'

    # IP patterns
    ipv4_re = r'(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}'
    ipv6_re = r'\[[0-9a-f:\.]+\]'  # (simple regex, validated later)

    # Host patterns
    hostname_re = r'[a-z' + ul + r'0-9](?:[a-z' + ul + r'0-9-]{0,61}[a-z' + ul + r'0-9])?'
    # Max length for domain name labels is 63 characters per RFC 1034 sec. 3.1
    domain_re = r'(?:\.(?!-)[a-z' + ul + r'0-9-]{1,63}(?<!-))*'
    tld_re = (
        r'\.'                                # dot
        r'(?!-)'                             # can't start with a dash
        r'(?:[a-z' + ul + '-]{2,63}'         # domain label
        r'|xn--[a-z0-9]{1,59})'              # or punycode label
        r'(?<!-)'                            # can't end with a dash
        r'\.?'                               # may have a trailing dot
    )
    host_re = '(' + hostname_re + domain_re + tld_re + '|localhost)'

    regex = re.compile(
        r'^(?:[a-z0-9\.\-\+]*)://'  # scheme is validated separately
        r'(?:\S+(?::\S*)?@)?'  # user:pass authentication
        r'(?:' + ipv4_re + '|' + ipv6_re + '|' + host_re + ')'
        r'(?::\d{2,5})?'  # port
        r'(?:[/?#][^\s]*)?'  # resource path
        r'\Z', re.IGNORECASE)
    message = 'Enter a valid URL'
    schemes = ['http', 'https', 'ftp', 'ftps']

    def __init__(self, schemes=None, **kwargs):
        super(URLValidator, self).__init__(**kwargs)
        if schemes is not None:
            self.schemes = schemes

    def __call__(self, value):
        value = to_text(value)
        scheme = value.split('://')[0].lower()
        if scheme not in self.schemes:
            raise ValidationError(self.message, code=self.code)

        # Then check full URL
        try:
            super(URLValidator, self).__call__(value)
        except ValidationError as e:
            # Trivial case failed. Try for possible IDN domain
            if value:
                try:
                    scheme, netloc, path, query, fragment = urlsplit(value)
                except ValueError:  # for example, "Invalid IPv6 URL"
                    raise ValidationError(self.message, code=self.code)
                try:
                    netloc = netloc.encode('idna').decode('ascii')  # IDN -> ACE
                except UnicodeError:  # invalid domain part
                    raise e
                url = urlunsplit((scheme, netloc, path, query, fragment))
                super(URLValidator, self).__call__(url)
            else:
                raise
        else:
            # Now verify IPv6 in the netloc part
            host_match = re.search(r'^\[(.+)\](?::\d{2,5})?$', urlsplit(value).netloc)
            if host_match:
                potential_ip = host_match.groups()[0]
                if not IPAddressValidator.check_ipv6(potential_ip):
                    raise ValidationError(self.message)

            # url = value

        # The maximum length of a full host name is 253 characters per RFC 1034
        # section 3.1. It's defined to be 255 bytes or less, but this includes
        # one byte for the length of the name and one byte for the trailing dot
        # that's used to indicate absolute names in DNS.
        if len(urlsplit(value).netloc) > 253:
            raise ValidationError(self.message)


IntegerValidator = RegexValidator(r'^-?\d+\Z', message='Enter a valid integer')


def validate_integer(value):
    return IntegerValidator(value)


class EmailValidator:
    message = 'Enter a valid email address'
    email_regex = re.compile(r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', re.IGNORECASE)

    def __init__(self, message=None):
        if message is not None:
            self.message = message

    def __call__(self, value):
        value = to_text(value)

        if not value or '@' not in value:
            raise ValidationError(self.message)

        if not self.email_regex.match(value):
            raise ValidationError(self.message)


ValidateEmail = EmailValidator()


class IPAddressValidator:
    """
    ipv4 或ipv6 地址是否合法
    """

    message = {
        "both": 'Enter a valid IPv4 or IPv6 address',
        "ipv4": 'Enter a valid IPv4 address',
        "ipv6": 'Enter a valid IPv6 address'
    }

    def __init__(self, protocol="both", message=None):
        self.protocol = protocol

        if message is not None:
            self.message = message

    def __call__(self, value):

        if not value or '\x00' in value:
            raise ValidationError(self.message[self.protocol])

        valid = True
        if self.protocol == "both":
            valid = self.is_valid_ip(value)

        elif self.protocol == "ipv4":
            valid = self.check_ipv4(value)

        elif self.protocol == "ipv6":
            valid = self.check_ipv6(value)

        if not valid:
            raise ValidationError(self.message[self.protocol])

    @classmethod
    def check_ipv4(cls, value):
        parts = value.split('.')

        if len(parts) == 4 and all(x.isdigit() for x in parts):
            numbers = list(int(x) for x in parts)
            return all(0 <= num < 256 for num in numbers)

        return False

    @classmethod
    def check_ipv6(cls, value):
        parts = value.split(':')
        if len(parts) > 8:
            return False

        num_blank = 0
        for part in parts:
            if not part:
                num_blank += 1
            else:
                try:
                    value = int(part, 16)
                except ValueError:
                    return False
                else:
                    if value < 0 or value >= 65536:
                        return False

        if num_blank < 2:
            return True
        elif num_blank == 2 and not parts[0] and not parts[1]:
            return True
        return False

    @classmethod
    def is_valid_ip(cls, ip):
        try:
            res = socket.getaddrinfo(ip, 0, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_NUMERICHOST)
            return bool(res)
        except socket.gaierror as e:
            return False
            # if e.args[0] == socket.EAI_NONAME:
            #     return False
            # raise


class BaseValidator:
    message = 'Ensure this value is %(limit_value)s (it is %(show_value)s)'

    def __init__(self, limit_value, message=None):
        self.limit_value = limit_value
        if message:
            self.message = message

    def __call__(self, value):
        cleaned = self.clean(value)
        params = {'limit_value': self.limit_value, 'show_value': cleaned, 'value': value}
        if self.compare(cleaned, self.limit_value):
            raise ValidationError(self.message, params=params)

    def compare(self, a, b):
        return a is not b

    def clean(self, x):
        return x


class MaxValueValidator(BaseValidator):
    message = 'Ensure this value is less than or equal to %(limit_value)s'

    def compare(self, a, b):
        return a > b


class MinValueValidator(BaseValidator):
    message = 'Ensure this value is greater than or equal to %(limit_value)s'

    def compare(self, a, b):
        return a < b


class MinLengthValidator(BaseValidator):
    message = 'Ensure this value has at least %(limit_value)d character (it has %(show_value)d)'

    def compare(self, a, b):
        return a < b

    def clean(self, x):
        return len(x)


class MaxLengthValidator(BaseValidator):
    message = 'Ensure this value has at most %(limit_value)d character (it has %(show_value)d)'

    def compare(self, a, b):
        return a > b

    def clean(self, x):
        return len(x)


class DecimalValidator:
    messages = {
        'max_digits': 'Ensure that there are no more than %(max)s digit in total',
        'max_decimal_places': 'Ensure that there are no more than %(max)s decimal place',
        'max_whole_digits': 'Ensure that there are no more than %(max)s digit before the decimal point'
    }

    def __init__(self, max_digits, decimal_places):
        self.max_digits = max_digits
        self.decimal_places = decimal_places

    def __call__(self, value):
        digit_tuple, exponent = value.as_tuple()[1:]
        decimals = abs(exponent)
        # digit_tuple doesn't include any leading zeros.
        digits = len(digit_tuple)
        if decimals > digits:
            # We have leading zeros up to or past the decimal point. Count
            # everything past the decimal point as a digit. We do not count
            # 0 before the decimal point as a digit since that would mean
            # we would not allow max_digits = decimal_places.
            digits = decimals
        whole_digits = digits - decimals

        if self.max_digits is not None and digits > self.max_digits:
            raise ValidationError(
                self.messages['max_digits'],
                params={'max': self.max_digits},
            )
        if self.decimal_places is not None and decimals > self.decimal_places:
            raise ValidationError(
                self.messages['max_decimal_places'],
                params={'max': self.decimal_places},
            )
        if (self.max_digits is not None and self.decimal_places is not None and
                whole_digits > (self.max_digits - self.decimal_places)):
            raise ValidationError(
                self.messages['max_whole_digits'],
                params={'max': (self.max_digits - self.decimal_places)},
            )


class FileExtensionValidator:
    message = "File extension '%(extension)s' is not allowed. Allowed extensions are: '%(allowed_extensions)s'."
    code = 'invalid_extension'

    def __init__(self, allowed_extensions=None, message=None):
        self.allowed_extensions = allowed_extensions
        if message is not None:
            self.message = message

    def __call__(self, value):
        extension = os.path.splitext(value.name)[1][1:].lower()
        if self.allowed_extensions is not None and extension not in self.allowed_extensions:
            raise ValidationError(
                self.message,
                params={
                    'extension': extension,
                    'allowed_extensions': ', '.join(self.allowed_extensions)
                }
            )


class PasswordValidator:
    """
    密码是否合法
    """
    message = {
        "number": "Enter a valid 6-digit password",
        "normal": "Enter a valid 6-18-digit alphanumeric password",
        "high": "Enter a 6-18 bit must contain any combination of upper "
                "and lower case letters, numbers, symbols password"
    }
    code = 'invalid'

    def __init__(self, level="number", message=None, regex=None):
        self.level = level

        if message is not None:
            self.message = message

        self.password_regex = re.compile(regex, flags=re.IGNORECASE) \
            if regex is not None else None

        if self.level == "number":
            self.password_regex = re.compile(r"^\d{6}$", flags=re.IGNORECASE)
        elif self.level == "normal":
            self.password_regex = re.compile(r"^(?![0-9]+$)(?![a-zA-Z]+$)[0-9A-Za-z]{6,18}$", flags=re.IGNORECASE)
        elif self.level == "high":
            re_str = r"^(?![0-9]+$)(?![a-z]+$)(?![A-Z]+$)(?!([^(0-9a-zA-Z\u4e00-\u9fa5\s)])+$)" \
                     r"([^(0-9a-zA-Z\u4e00-\u9fa5\s)]|[a-z]|[A-Z]|[0-9]){6,18}$"
            self.password_regex = re.compile(re_str, flags=re.IGNORECASE)

    def __call__(self, value):
        if self.level == "any" or self.password_regex is None:
            return

        valid = self.password_regex.match(value)

        if not valid:
            raise ValidationError(self.message[self.level])


class PhoneValidator:
    """
    手机号码检查
    移动号段：
    134 135 136 137 138 139 147 148 150 151 152 157 158 159 172 178 182 183 184 187 188 198
    联通号段：
    130 131 132 145 146 155 156 166 171 175 176 185 186
    电信号段：
    133 149 153 173 174 177 180 181 189 199
    虚拟运营商:
    170
    2017-08-08：工信部新批号段：电信199/移动198/联通166 ，146联通，148移动

    精准的匹配：^(13[0-9]|14[5-9]|15[0-9]|16[6]|17[0-8]|18[0-9]|19[8-9])\d{8}$
    粗准匹配：^1(3|4|5|7|8|9)[0-9]{9}$
    """
    message = "Enter a valid phone number"
    phone_regex = re.compile(
        r"^(13[0-9]|14[5-9]|15[0-9]|16[6]|17[0-8]|18[0-9]|19[8-9])\d{8}$",
        flags=re.IGNORECASE
    )

    def __init__(self, message=None, regex=None):
        if message is not None:
            self.message = message
        if regex is not None:
            self.phone_regex = re.compile(regex, flags=re.IGNORECASE)

    def __call__(self, value):
        value = to_text(value)

        if not value or not value.isdigit():
            raise ValidationError(self.message)

        if not self.phone_regex.match(value):
            raise ValidationError(self.message)


ValidatePhone = PhoneValidator()


class IdentifierValidator:
    """
    手机号码或邮箱地址是否合法
    """

    message = {
        "both": "Enter a valid phone number or email address",
        "phone": "Enter a valid phone number",
        "email": "Enter a valid email address"
    }

    def __init__(self, protocol="both", message=None):
        self.protocol = protocol
        if message is not None:
            self.message = message

    def __call__(self, value):
        if not value:
            raise ValidationError(self.message[self.protocol])

        if self.protocol == "both":
            if "@" in value:
                ValidateEmail(value)
            elif value.isdigit():
                ValidatePhone(value)
            else:
                raise ValidationError(self.message[self.protocol])

        elif self.protocol == "email":
            ValidateEmail(value)

        elif self.protocol == "phone":
            ValidatePhone(value)
