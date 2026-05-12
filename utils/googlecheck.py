from .certs import Certs
from cache_data import Manifest
from collections import Counter
from cryptography import x509
from datetime import datetime, timedelta
from downloaders.downloader import Downloader
from json import JSONDecodeError
from pathlib import Path
from program.keytype import KeyType
from time import time
from typing import final, overload, ClassVar, Literal, Self, TypedDict, NotRequired
from xml.etree.ElementTree import Element
import __main__
import json


"""
Thanks to https://github.com/Ante0/YetAnotherKeyboxChecker
and https://github.com/Transwarpcom/Check-Keybox-Certificate-Revocation-Status

Also see https://developer.android.com/privacy-and-security/security-key-attestation#certificate_status
"""


class Attestation(TypedDict):
    status: Literal['REVOKED', 'SUSPENDED']
    reason: NotRequired[
        Literal[
            'UNSPECIFIED',
            'KEY_COMPROMISE',
            'CA_COMPROMISE',
            'SUPERSEDED',
            'SOFTWARE_FLAW',
        ]
    ]


class AttestationList(TypedDict):
    entries: dict[str, Attestation]


@final
class GoogleChecker(Certs):
    URL = f'https://android.googleapis.com/attestation/status?{time():.0f}'
    AOSP_CERTS = Counter((0x1001, 0x00A2059ED10E435B57, 0x1000, 0x00FF94D9DD9F07C80C))

    root: Path = __main__.exe_root
    cache_folder = root / 'cache'
    cached = cache_folder / 'attestation.json'

    revoked: ClassVar[set[str]]
    status_list: ClassVar[AttestationList]

    @classmethod
    async def init(cls):
        cls.cache_folder.mkdir(exist_ok=True)
        cls.cached.touch(exist_ok=True)

        with open(cls.cached, 'r+') as cached_status:
            manifest = Manifest()
            do_download = False

            try:
                cls.status_list = json.load(cached_status)
            except JSONDecodeError:
                do_download = True

            if not do_download and manifest.attestation_date > 0:
                time_diff = datetime.now() - datetime.fromtimestamp(
                    manifest.attestation_date
                )

                if (time_diff / timedelta(hours=1)) >= 24:
                    do_download = True

            if do_download:
                data = await Downloader.client.get(cls.URL)
                cls.status_list = data.json()

                cached_status.seek(0)
                cached_status.truncate()
                json.dump(cls.status_list, cached_status)

                manifest.attestation_date = datetime.now().timestamp()

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
    ) -> KeyType: ...

    async def is_keybox_valid(
        self, xml: Element, per_key=False
    ) -> KeyType | dict[str, bool]:
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
            keys[parsed_serials[0]] = False if found else True

        if per_key:
            return keys
        else:
            if all(keys.values()):
                return KeyType.AOSP if self.is_aosp_keybox(xml) else KeyType.VALID
            elif next(iter(keys.values())):
                return KeyType.SEMI_VALID
            else:
                return KeyType.REVOKED

    def is_aosp_keybox(self, xml: Element) -> bool:
        return (
            Counter(cert.serial_number for cert in self.get_certs(keybox=xml))
            == self.AOSP_CERTS
        )
