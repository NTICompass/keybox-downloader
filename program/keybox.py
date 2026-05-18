from __future__ import annotations
from cache_data import Manifest
from collections import defaultdict, Counter
from cryptography import x509
from cryptography.x509.base import Certificate
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum, auto
from httpx import AsyncClient
from io import IOBase
from json import JSONDecodeError
from logging import Logger
from pathlib import Path
from time import time
from typing import (
    final,
    ClassVar,
    Literal,
    TypedDict,
    NotRequired,
    Self,
    TYPE_CHECKING,
    override,
)
from xml.etree.ElementTree import Element, ElementTree, ParseError
from zipfile import Path as ZipPath
import __main__
import json
import logging
import xml.etree.ElementTree as ET

if TYPE_CHECKING:
    from downloaders import Downloader


class KeyType(StrEnum):
    VALID = auto()
    SEMI_VALID = auto()
    REVOKED = auto()
    AOSP = auto()


@dataclass
class KeyboxMetadata:
    file_idx: int = 0
    source: type[Downloader] | None = None
    original: Path | ZipPath | None = None

    @property
    def name(self) -> str:
        return f'{self.source.__name__ if self.source is not None else "keybox"}_{self.file_idx:d}.xml'


class KeyboxError(SyntaxError):
    @override
    def __init__(self, msg: str, orig_err: ParseError):
        super().__init__(msg)
        self.original_error: ParseError = orig_err


# See: https://developer.android.com/privacy-and-security/security-key-attestation#certificate_status
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
class Keybox:
    root: Element
    meta: KeyboxMetadata
    logger: Logger

    _cert_data: list[Certificate]
    _cert_counts: tuple[int, int]
    _cert_valid: dict[int, bool]

    revoked: ClassVar[set[str]]
    status_list: ClassVar[AttestationList]

    _root: ClassVar[Path] = __main__.exe_root
    _cache_folder: ClassVar[Path] = _root / 'cache'
    _cached: ClassVar[Path] = _cache_folder / 'attestation.json'

    _URL: ClassVar[str] = (
        f'https://android.googleapis.com/attestation/status?{time():.0f}'
    )
    _AOSP_CERTS: ClassVar[Counter[int]] = Counter(
        (0x1001, 0x00A2059ED10E435B57, 0x1000, 0x00FF94D9DD9F07C80C)
    )

    def __init__(
        self,
        keybox_data: Element | Path | IOBase | str | bytes,
        metadata: KeyboxMetadata | None = None,
    ):
        if isinstance(keybox_data, Element):
            self.root = keybox_data
        elif isinstance(keybox_data, (Path, IOBase)):
            self.root = ET.parse(keybox_data).getroot()
        elif isinstance(keybox_data, (str, bytes)):
            try:
                self.root = ET.fromstring(keybox_data)
            except ParseError as e:
                raise KeyboxError(f'Cannot parse "{keybox_data}"', e)

        # Fix certs, remove excess new lines
        for cert in self.root.iterfind('.//Keybox//Certificate[@format="pem"]'):
            if cert.text:
                # From: https://stackoverflow.com/a/17610612
                cert.text = '\n'.join(
                    [ll.rstrip() for ll in cert.text.splitlines() if ll.strip()]
                )

        # Probably fix the private keys, too
        for key in self.root.iterfind('.//Keybox//PrivateKey[@format="pem"]'):
            if key.text:
                key.text = '\n'.join(
                    [ll.rstrip() for ll in key.text.splitlines() if ll.strip()]
                )

        self.meta = metadata if metadata is not None else KeyboxMetadata()
        self.logger = logging.getLogger(
            f'{type(self).__name__}.{self.meta.original.stem if self.meta.original is not None else ""}'
        )

        self.__load_certs()

    @classmethod
    async def init_attestation(cls, dl: AsyncClient):
        cls._cache_folder.mkdir(exist_ok=True)
        cls._cached.touch(exist_ok=True)

        with open(cls._cached, 'r+') as cached_status:
            manifest = Manifest()
            do_download = False

            try:
                cls.status_list = json.load(cached_status)
            except JSONDecodeError:
                do_download = True

            if not do_download and manifest.attestation_date >= 0:
                time_diff = datetime.now() - datetime.fromtimestamp(
                    manifest.attestation_date
                )

                if (time_diff / timedelta(hours=1)) >= 24:
                    do_download = True

            if do_download:
                data = await dl.get(cls._URL)
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

    type KeyboxGroup = defaultdict[frozenset[tuple[int, int]], list[str]]

    @classmethod
    def group(cls, *keyboxes: Self) -> KeyboxGroup:
        groups: cls.KeyboxGroup = defaultdict(list)

        for keybox in keyboxes:
            key = frozenset(keybox.serials.items())
            name = keybox.device_id

            groups[key].append(
                name
                if name is not None
                else str(
                    keybox.meta.original.stem
                    if keybox.meta.original is not None
                    else ''
                )
            )

        return groups

    def save(self, folder: Path):
        file_name = folder / self.meta.name
        self.logger.info(f'Saving keybox to {file_name}')

        ElementTree(self.root).write(file_name, 'unicode', True)

    def __load_certs(self):
        self.logger.info('Loading certs from keybox')

        ec_certs = self.root.findall(
            './/Key[@algorithm="ecdsa"]/CertificateChain/Certificate'
        )
        rsa_certs = self.root.findall(
            './/Key[@algorithm="rsa"]/CertificateChain/Certificate'
        )

        self._cert_counts = (len(ec_certs), len(rsa_certs))
        self.logger.info(
            f'Found {self._cert_counts[0]} EC and {self._cert_counts[1]} RSA certs for "{self.device_id}"'
        )

        try:
            self._cert_data = x509.load_pem_x509_certificates(
                b''.join(
                    cert_pem.text.encode()
                    for cert_pem in ec_certs
                    if cert_pem.text is not None
                )
                + b''.join(
                    cert_pem.text.encode()
                    for cert_pem in rsa_certs
                    if cert_pem.text is not None
                )
            )
        except ValueError:
            self._cert_data = []

    def __is_aosp_keybox(self) -> bool:
        return self.serials == self._AOSP_CERTS

    def __check_cert_validity(self):
        if not hasattr(self, 'status_list'):
            raise RuntimeError(
                f'Please load attestation status with "await {type(self).__name__}.init_attestation()"'
            )

        self._cert_valid: dict[int, bool] = {}

        for cert in self._cert_data:
            self.logger.info(
                f'Valid between {cert.not_valid_before_utc:%a %b %d %Y, %I:%M%p} '
                f'and {cert.not_valid_after_utc:%a %b %d %Y, %I:%M%p}'
            )

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
            self._cert_valid[cert.serial_number] = False if found else True

    @property
    def serials(self) -> Counter[int]:
        return Counter(cert.serial_number for cert in self._cert_data)

    @property
    def key_type(self) -> KeyType:
        if not hasattr(self, '_cert_valid'):
            self.__check_cert_validity()

        if all(self._cert_valid.values()):
            return KeyType.AOSP if self.__is_aosp_keybox() else KeyType.VALID
        elif next(iter(self._cert_valid.values())):
            return KeyType.SEMI_VALID
        else:
            return KeyType.REVOKED

    @property
    def keys_valid(self) -> dict[str, bool]:
        if not hasattr(self, '_cert_valid'):
            self.__check_cert_validity()

        return {f'{key:x}': valid for key, valid in self._cert_valid.items()}

    @property
    def key_counts(self) -> tuple[int, int]:
        return self._cert_counts

    @property
    def device_id(self) -> str | None:
        device = self.root.find('.//Keybox[@DeviceID]')
        return device.get('DeviceID') if device is not None else None

    @device_id.setter
    def device_id(self, value: str):
        device = self.root.find('.//Keybox')

        if device is not None:
            device.set('DeviceID', value)
