from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
import dateparser
import re
import subprocess


class x509:
    """
    If we don't have the `cryptography` module, then use this module to call `openssl` from the command line
    """
    BEGIN = '-----BEGIN CERTIFICATE-----'
    END = '-----END CERTIFICATE-----'

    def load_pem_x509_certificates(self, data: bytes) -> list[x509_cert]:
        return [x509_cert(cert) for cert in re.findall(rf'{self.BEGIN}.+?{self.END}', data.decode('ascii'))]


@dataclass(repr=False, eq=False)
class x509_cert:
    """
    To get info about the cert, use `openssl x509 -inform pem -noout -text`
    https://docs.openssl.org/3.6/man1/openssl-x509/
    """
    cert: str

    def get_from_openssl(self, field: str) -> list[str]:
        openssl = subprocess.run(['openssl', 'x509', '-inform', 'pem', '-noout', f'-{field}'], input=self.cert, text=True, capture_output=True)
        return openssl.stdout.strip().split('=', maxsplit=1)

    def read_openssl_value(self, field: list[str] | str, convert: Callable[[str], Any]) -> Any:
        ssl_fields = [field] * 2 if isinstance(field, str) else field
        data = self.get_from_openssl(ssl_fields[0])

        if data[0] == ssl_fields[1]:
            return convert(data[1])
        else:
            raise ValueError

    @property
    def not_valid_before_utc(self) -> datetime:
        return self.read_openssl_value(
            ['startdate', 'notBefore'], lambda date: dateparser.parse(date)
        )

    @property
    def not_valid_after_utc(self) -> datetime:
        return self.read_openssl_value(
            ['enddate', 'notAfter'], lambda date: dateparser.parse(date)
        )

    @property
    def serial_number(self) -> int:
        return self.read_openssl_value(
            'serial', lambda serial: int(serial[1], 16)
        )
