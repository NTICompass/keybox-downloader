from cryptography import x509
from glob import glob
import json
import logging
import xml.etree.ElementTree as ET


class Duplicate:
    def __init__(self, folder: str, extras: bool = True):
        self.logger = logging.getLogger(type(self).__name__)
        self.files: list[str] = glob(f'{folder.rstrip('/')}/**/*.xml', recursive=True)
        self.certs: dict[str, set[str]] = {}

        if extras:
            self.files.extend(glob('extra/**/*.xml', recursive=True))

        self.logger.info(f'Loading {len(self.files)} files in {folder}')

    def check_duplicates(self):
        self.group_keyboxes()
        self.logger.info(f'Results:\n{json.dumps(self.certs, indent=4, default=lambda x: list(x) if isinstance(x, set) else x)}')

    def group_keyboxes(self):
        for file in self.files:
            self.logger.info(f'Parsing XML file {file}')

            keybox = ET.parse(file)
            root = keybox.getroot()

            ec_certs = root.findall('.//Key[@algorithm="ecdsa"]/CertificateChain/Certificate')
            rsa_certs = root.findall('.//Key[@algorithm="rsa"]/CertificateChain/Certificate')
            self.logger.info(f'Found {len(ec_certs)} EC and {len(rsa_certs)} RSA certs')

            certs = x509.load_pem_x509_certificates(
                b''.join(cert_pem.text.encode() for cert_pem in ec_certs) +
                b''.join(cert_pem.text.encode() for cert_pem in rsa_certs)
            )

            for cert in certs:
                hex_serial = f'{cert.serial_number:x}'
                issuer_serial = {attr.value.lower() for attr in cert.issuer if attr.oid == x509.NameOID.SERIAL_NUMBER}
                cert_key = f'{hex_serial}_{issuer_serial.pop()}'

                self.logger.info(f'Valid between {cert.not_valid_before_utc:%a %b %d %Y, %I:%M%p} and {cert.not_valid_after_utc:%a %b %d %Y, %I:%M%p}')

                if cert_key not in self.certs:
                    self.certs[cert_key] = set()

                self.certs[cert_key].add(file)