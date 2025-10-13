from cryptography import x509
from glob import glob
from utils.certs import Certs
import json
import xml.etree.ElementTree as ET


class Duplicate(Certs):
    def __init__(self, folder: str, extras: bool = True):
        super().__init__()
        self.files: list[str] = glob(f'{folder.rstrip("/")}/**/*.xml', recursive=True)
        self.certs: dict[str, set[str]] = {}

        if extras:
            self.files.extend(glob('extra/**/*.xml', recursive=True))

        self.logger.info(f'Loading {len(self.files)} files in {folder}')

    def check_duplicates(self):
        self.group_keyboxes()
        self.logger.info(
            f'Results:\n{json.dumps(self.certs, indent=4, default=lambda x: list(x) if isinstance(x, set) else x)}'
        )

    def group_keyboxes(self):
        for file in self.files:
            self.logger.info(f'Parsing XML file {file}')

            keybox = ET.parse(file)
            root = keybox.getroot()

            for cert in self.get_certs(keybox=root):
                hex_serial = f'{cert.serial_number:x}'
                issuer_serial = {
                    attr.value.lower()
                    for attr in cert.issuer
                    if attr.oid == x509.NameOID.SERIAL_NUMBER
                }
                cert_key = f'{hex_serial}_{issuer_serial.pop()}'

                if cert_key not in self.certs:
                    self.certs[cert_key] = set()

                self.certs[cert_key].add(file)
