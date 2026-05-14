from cryptography import x509
from cryptography.x509.base import Certificate
from dataclasses import dataclass, field
from logging import Logger
from pathlib import Path
from program.keytype import KeyType
from xml.etree.ElementTree import ElementTree, Element
import logging


@dataclass
class Keybox:
    file: ElementTree | None = None
    root: Element | None = None

    _cert_data: dict[int, list[Certificate]] = field(init=False, repr=False)
    _cert_counts: dict[int, tuple[int, int]] = field(init=False, repr=False)
    _logger: Logger = field(init=False, repr=False)

    def __post_init__(self):
        if self.file is not None and self.root is None:
            self.root = self.file.getroot()
        elif self.root is not None and self.file is None:
            self.file = ElementTree(self.root)
        else:
            raise ValueError('Either file or root needs to be set')

        name = self.device_id
        self._logger = logging.getLogger(
            f'{type(self).__name__}.{name if name is not None else "unnamed"}'
        )

    @property
    def type(self) -> KeyType:
        return KeyType.VALID

    @property
    def device_id(self) -> str | None:
        if self.root is not None:
            device = self.root.find('.//Keybox[@DeviceID]')
            return device.get('DeviceID') if device is not None else None

        return None

    @device_id.setter
    def device_id(self, value: str):
        if self.root is not None:
            device = self.root.find('.//Keybox')

            if device is not None:
                device.set('DeviceID', value)

    def save(self, file: Path):
        if self.file is not None:
            self.file.write(file, 'unicode', True)
