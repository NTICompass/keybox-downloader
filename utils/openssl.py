from collections.abc import Callable, Generator
from dataclasses import dataclass
from datetime import datetime
from typing import Any, NamedTuple
import dateparser
import re
import subprocess

BEGIN = '-----BEGIN CERTIFICATE-----'
END = '-----END CERTIFICATE-----'


@dataclass(repr=False)
class ObjectIdentifier:
    title: str


class NameValue(NamedTuple):
    oid: ObjectIdentifier
    value: str


class Name:
    def __init__(self, data: dict[str, str]):
        self.values = data

    def __iter__(self) -> Generator[NameValue]:
        return (NameValue(oid=ObjectIdentifier(key), value=value) for key, value in self.values.items())


@dataclass(repr=False, eq=False)
class NameOIDValue:
    SERIAL_NUMBER = ObjectIdentifier('serialNumber')


class x509:
    """
    If we don't have the `cryptography` module, then use this module to call `openssl` from the command line
    """

    NameOID = NameOIDValue()

    @staticmethod
    def load_pem_x509_certificates(data: bytes) -> list[x509_cert]:
        return [x509_cert(cert) for cert in re.findall(rf'{BEGIN}.+?{END}', data.decode('ascii'), re.DOTALL)]


@dataclass(repr=False, eq=False)
class x509_cert:
    """
    To get info about the cert, use `openssl x509 -inform pem -noout -text`
    https://docs.openssl.org/3.6/man1/openssl-x509/
    """

    cert: str

    def get_from_openssl(self, field: str) -> list[str]:
        openssl = subprocess.run(
            ['openssl', 'x509', '-inform', 'pem', '-noout', f'-{field}'],
            input=''.join(line.lstrip() for line in self.cert.splitlines(keepends=True)),
            text=True,
            capture_output=True
        )
        return openssl.stdout.strip().split('=', maxsplit=1)

    def read_openssl_value(self, field: list[str] | str, convert: Callable[[str], Any]) -> Any:
        in_field, out_field = [field] * 2 if isinstance(field, str) else field
        data_field, data_value = self.get_from_openssl(in_field)

        if data_field == out_field:
            return convert(data_value)
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
            'serial', lambda serial: int(serial, 16)
        )

    @property
    def issuer(self) -> Name:
        data: dict[str, str] = self.read_openssl_value(
            'issuer',
            lambda issuer: dict(issuer_value.split('=', maxsplit=1) for issuer_value in re.split(r',\s+', issuer))
        )

        return Name(data)
