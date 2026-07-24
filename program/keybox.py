# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""`Keybox` module to wrap `xml.etree.ElementTree` objects."""

import logging
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum, auto
from io import IOBase
from logging import Logger
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, ClassVar, Literal, Self, final
from xml.etree.ElementTree import Element, ElementTree, ParseError

from cryptography import x509
from pydantic import BaseModel, ConfigDict, Field

import __main__
from cache_data import Manifest

if TYPE_CHECKING:
    from zipfile import Path as ZipPath

    from cryptography.x509.base import Certificate
    from httpx2 import AsyncClient


class KeyType(StrEnum):
    """Folder to sort each `Keybox` into."""

    VALID = auto()
    SEMI_VALID = auto()
    REVOKED = auto()
    AOSP = auto()


@dataclass
class KeyboxMetadata:
    """Information about each `Keybox`, including its source."""

    file_idx: int = 0
    source: str = ''
    original: Path | ZipPath | None = None

    @property
    def name(self) -> str:
        """The file name to save the `Keybox` as.

        Returns:
            source_idx.xml

        """
        return f'{self.source if len(self.source) > 0 else "keybox"}_{self.file_idx:d}.xml'


class KeyboxError(ValueError):
    """Custom error when an XML string cannot be read."""


class Attestation(BaseModel):  # ruff: ignore[undocumented-public-class]
    model_config = ConfigDict(frozen=True)
    status: Literal['REVOKED', 'SUSPENDED']
    reason: Literal['UNSPECIFIED', 'KEY_COMPROMISE', 'CA_COMPROMISE', 'SUPERSEDED', 'SOFTWARE_FLAW'] | None = None
    expires: str | None = None
    comment: str | None = Field(default=None, max_length=140)


class AttestationList(BaseModel):
    """Attestation status from Google.

    Docs: https://developer.android.com/privacy-and-security/security-key-attestation#certificate_status
    """

    model_config = ConfigDict(frozen=True)
    entries: dict[str, Attestation]


dl_hours = 24
local_tz = datetime.now(UTC).astimezone().tzinfo


@final
class Keybox:
    """`ElementTree` Wrapper class to read certificates from a keybox.xml."""

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

    _URL: ClassVar[str] = f'https://android.googleapis.com/attestation/status?{time():.0f}'
    _AOSP_CERTS: ClassVar[Counter[int]] = Counter((0x1001, 0x00A2059ED10E435B57, 0x1000, 0x00FF94D9DD9F07C80C))

    def __init__(
        self, keybox_data: Element | Path | IOBase | str | bytes, metadata: KeyboxMetadata | None = None
    ) -> None:
        """Wrap a keybox.xml file.

        Args:
            keybox_data: The XML file to load
            metadata: A `KeyboxMetadata` object to attach

        Raises:
            KeyboxError: If the XML cannot be parsed

        """
        if isinstance(keybox_data, Element):
            self.root = keybox_data
        elif isinstance(keybox_data, (Path, IOBase)):
            self.root = ET.parse(keybox_data).getroot()
        elif isinstance(keybox_data, (str, bytes)):
            try:
                self.root = ET.fromstring(keybox_data)
            except ParseError as e:
                msg = f'Cannot parse "{keybox_data}"'
                raise KeyboxError(msg) from e

        # Fix certs, remove excess new lines
        for cert in self.root.iterfind('.//Keybox//Certificate[@format="pem"]'):
            if cert.text:
                # From: https://stackoverflow.com/a/17610612
                cert.text = '\n'.join([ll.rstrip() for ll in cert.text.splitlines() if ll.strip()])

        # Probably fix the private keys, too
        for key in self.root.iterfind('.//Keybox//PrivateKey[@format="pem"]'):
            if key.text:
                key.text = '\n'.join([ll.rstrip() for ll in key.text.splitlines() if ll.strip()])

        self.meta = metadata if metadata is not None else KeyboxMetadata()
        self.logger = logging.getLogger(
            f'{type(self).__name__}.{self.meta.original.stem if self.meta.original is not None else ""}'
        )

        self.__load_certs()

    @classmethod
    async def init_attestation(cls, dl: AsyncClient) -> None:
        """Download the Attestation status from Google (or use cached version).

        Args:
            dl: The `AsyncClient` from `httpx2`

        """
        cls._cache_folder.mkdir(exist_ok=True)
        cls._cached.touch(exist_ok=True)

        with Path(cls._cached).open('r+') as cached_status:
            manifest = Manifest()
            cache_json = cached_status.read()
            do_download = len(cache_json) == 0

            if not do_download and manifest.attestation_date >= 0:
                time_diff = datetime.now(tz=local_tz) - datetime.fromtimestamp(manifest.attestation_date, tz=local_tz)

                if (time_diff / timedelta(hours=1)) >= dl_hours:
                    do_download = True

            if not do_download:
                cls.status_list = AttestationList.model_validate_json(cache_json)
            else:
                data = await dl.get(cls._URL)
                cls.status_list = AttestationList.model_validate(data.json())

                cached_status.seek(0)
                cached_status.truncate()
                cached_status.write(cls.status_list.model_dump_json())

                manifest.attestation_date = datetime.now(tz=local_tz).timestamp()

            cls.revoked = {key for key, status in cls.status_list.entries.items() if status.status == 'REVOKED'}

    type KeyboxGroup = defaultdict[frozenset[tuple[int, int]], list[str]]

    @classmethod
    def group(cls, *keyboxes: Self) -> KeyboxGroup:
        """Group keyboxes by their serials.

        Args:
            keyboxes: The `Keybox` objects to group

        Returns:
            A dict of keys and keybox names

        """
        groups: cls.KeyboxGroup = defaultdict(list)

        for keybox in keyboxes:
            key = frozenset(keybox.serials.items())
            name = keybox.device_id

            groups[key].append(
                name if name is not None else str(keybox.meta.original.stem if keybox.meta.original is not None else '')
            )

        return groups

    def save(self, folder: Path) -> None:
        """Save the keybox into an XML file.

        Args:
            folder: Where to save the file to

        """
        file_name = folder / self.meta.name
        self.logger.info('Saving keybox to %s', file_name)

        ElementTree(self.root).write(file_name, 'unicode', xml_declaration=True)

    def __load_certs(self) -> None:
        """Read the certificates from the XML and save them into `self._cert_data`."""
        self.logger.info('Loading certs from keybox')

        ec_certs = self.root.findall('.//Key[@algorithm="ecdsa"]/CertificateChain/Certificate')
        rsa_certs = self.root.findall('.//Key[@algorithm="rsa"]/CertificateChain/Certificate')

        self._cert_counts = (len(ec_certs), len(rsa_certs))
        self.logger.info(f'Found {self._cert_counts[0]} EC and {self._cert_counts[1]} RSA certs for "{self.device_id}"')

        try:
            self._cert_data = x509.load_pem_x509_certificates(
                b''.join(cert_pem.text.encode() for cert_pem in ec_certs if cert_pem.text is not None)
                + b''.join(cert_pem.text.encode() for cert_pem in rsa_certs if cert_pem.text is not None)
            )
        except ValueError:
            self._cert_data = []

    @property
    def __is_aosp_keybox(self) -> bool:
        return self.serials == self._AOSP_CERTS

    def __check_cert_validity(self) -> None:
        """Check the XML against Google's Attestation status (saves into `self._cert_valid`).

        Raises:
            RuntimeError: If Attestation status is not loaded (call `init_attestation()`)

        """
        if not hasattr(self, 'status_list'):
            msg = f'Please load attestation status with "await {type(self).__name__}.init_attestation()"'
            raise RuntimeError(msg)

        self._cert_valid: dict[int, bool] = {}

        for cert in self._cert_data:
            self.logger.info(
                f'Valid between {cert.not_valid_before_utc:%a %b %d %Y, %I:%M%p} '
                f'and {cert.not_valid_after_utc:%a %b %d %Y, %I:%M%p}'
            )

            issuer_serial = {attr.value.lower() for attr in cert.issuer if attr.oid == x509.NameOID.SERIAL_NUMBER}

            parsed_serials = (f'{cert.serial_number:x}', str(issuer_serial.pop()) if len(issuer_serial) > 0 else None)

            self.logger.info('Parsed cert {}, issuer {}'.format(*parsed_serials))
            found = (parsed_serials[0] and parsed_serials[0] in self.revoked) or (
                parsed_serials[1] and parsed_serials[1] in self.revoked
            )

            self.logger.info('Cert is revoked' if found else 'Cert is valid')
            self._cert_valid[cert.serial_number] = not found

    @property
    def serials(self) -> Counter[int]:
        """Group the serial numbers for all the certs in this XML file.

        Returns:
            `Counter` of serial numbers

        """
        return Counter(cert.serial_number for cert in self._cert_data)

    @property
    def key_type(self) -> KeyType:
        """What type of key this is (what folder do we store it in?).

        Returns:
            `KeyType`

        """
        if not hasattr(self, '_cert_valid'):
            self.__check_cert_validity()

        if all(self._cert_valid.values()):
            return KeyType.AOSP if self.__is_aosp_keybox else KeyType.VALID
        if next(iter(self._cert_valid.values())):
            return KeyType.SEMI_VALID
        return KeyType.REVOKED

    @property
    def keys_valid(self) -> dict[str, bool]:
        """Which certs in this XML file are valid.

        Returns:
            Map of serials to their validity

        """
        if not hasattr(self, '_cert_valid'):
            self.__check_cert_validity()

        return {f'{key:x}': valid for key, valid in self._cert_valid.items()}

    @property
    def key_counts(self) -> tuple[int, int]:
        """How many of each cert (EC/RSA) does this XML have.

        Returns:
            EC cert count, RSA cert count

        """
        return self._cert_counts

    @property
    def device_id(self) -> str | None:
        """The XML's `DeviceID` (if it has one).

        Returns:
            DeviceID or `None`

        """
        device = self.root.find('.//Keybox[@DeviceID]')
        return device.get('DeviceID') if device is not None else None

    @device_id.setter
    def device_id(self, value: str) -> None:
        """Set the DeviceID on the XML file.

        Args:
            value: The new DeviceID

        """
        device = self.root.find('.//Keybox')

        if device is not None:
            device.set('DeviceID', value)
