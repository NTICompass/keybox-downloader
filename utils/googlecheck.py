from .certs import Certs
from collections import Counter
from cryptography import x509
from downloaders.downloader import Downloader
from time import time
from typing import final, overload, ClassVar, Literal, Self, TypedDict
from xml.etree.ElementTree import Element


"""
Thanks to https://github.com/Ante0/YetAnotherKeyboxChecker
and https://github.com/Transwarpcom/Check-Keybox-Certificate-Revocation-Status

Also see https://developer.android.com/privacy-and-security/security-key-attestation
"""


class Attestation(TypedDict):
    status: str  # REVOKED
    reason: str  # KEY_COMPROMISE


class AttestationList(TypedDict):
    entries: dict[str, Attestation]


@final
class GoogleChecker(Certs):
    URL = f'https://android.googleapis.com/attestation/status?{time():.0f}'
    AOSP_CERTS = Counter((0x1001, 0x00A2059ED10E435B57, 0x1000, 0x00FF94D9DD9F07C80C))

    revoked: ClassVar[set[str]]
    status_list: ClassVar[AttestationList]

    @classmethod
    async def init(cls):
        data = await Downloader.client.get(cls.URL)
        cls.status_list = data.json()

        cls.revoked = {
            key
            for key, status in cls.status_list['entries'].items()
            if status['status'] == 'REVOKED'
        }

    @classmethod
    async def get_instance(cls) -> Self:
        instance = cls()
        await cls.init()

        return instance

    @overload
    async def is_keybox_valid(
        self, xml: Element, per_key: Literal[True]
    ) -> dict[str, bool]: ...

    @overload
    async def is_keybox_valid(
        self, xml: Element, per_key: Literal[False] = False
    ) -> bool: ...

    async def is_keybox_valid(
        self, xml: Element, per_key=False
    ) -> bool | dict[str, bool]:
        keys: dict[str, bool] = {}

        if not hasattr(self, 'status_list'):
            raise RuntimeError(
                'Please load attestation status with GoogleChecker.init()'
            )

        for cert in self.get_certs(log_valid=True, key=self.load_certs(xml)):
            issuer_serial = {
                attr.value.lower()
                for attr in cert.issuer
                if attr.oid == x509.NameOID.SERIAL_NUMBER
            }
            parsed_serials = (
                f'{cert.serial_number:x}',
                str(issuer_serial.pop()) if len(issuer_serial) > 0 else None,
            )

            self.logger.info('Parsed cert {}, issuer {}'.format(*parsed_serials))

            found = (parsed_serials[0] and parsed_serials[0] in self.revoked) or (
                parsed_serials[1] and parsed_serials[1] in self.revoked
            )
            self.logger.info('Cert is revoked' if found else 'Cert is valid')

            if per_key:
                keys[parsed_serials[0]] = False if found else True
            elif found:
                return False

        return keys if per_key else True

    def is_aosp_keybox(self, xml: Element) -> bool:
        return (
            Counter(cert.serial_number for cert in self.get_certs(keybox=xml))
            == self.AOSP_CERTS
        )
