from .keytype import KeyType
from cryptography import x509
from cryptography.x509.base import Certificate
from dataclasses import dataclass
from downloaders import Downloader
from io import BytesIO
from logging import Logger
from pathlib import Path
from typing import final
from xml.etree.ElementTree import Element, ElementTree
import logging
import xml.etree.ElementTree as ET


@dataclass
class KeyboxMetadata:
    file_idx: int
    source: type[Downloader]
    original: Path

    @property
    def name(self) -> str:
        return f'{self.source.__name__}_{self.file_idx:d}.xml'


@final
class Keybox:
    root: Element
    meta: KeyboxMetadata
    logger: Logger

    _cert_data: list[Certificate]
    _cert_counts: tuple[int, int]

    def __init__(
        self,
        keybox_data: Element | Path | BytesIO | str,
        metadata: KeyboxMetadata,
    ):
        if isinstance(keybox_data, Element):
            self.root = keybox_data
        elif isinstance(keybox_data, (Path, BytesIO)):
            self.root = ET.parse(keybox_data).getroot()
        elif isinstance(keybox_data, str):
            self.root = ET.fromstring(keybox_data)

        self.meta = metadata
        self.logger = logging.getLogger(
            f'{type(self).__name__}.{self.meta.original.stem}'
        )

        self.__load_certs()

    def save(self, folder: Path):
        ElementTree(self.root).write(folder / self.meta.name, 'unicode', True)

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

    @property
    def key_type(self) -> KeyType:
        # TODO: Add logic
        return KeyType.VALID

    @property
    def device_id(self) -> str | None:
        device = self.root.find('.//Keybox[@DeviceID]')
        return device.get('DeviceID') if device is not None else None

    @device_id.setter
    def device_id(self, value: str):
        device = self.root.find('.//Keybox')

        if device is not None:
            device.set('DeviceID', value)
