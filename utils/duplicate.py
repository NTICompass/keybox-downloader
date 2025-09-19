from cryptography import x509
from glob import glob
import json
import logging
import xml.etree.ElementTree as ET


class Duplicate:
    def __init__(self, folder: str):
        self.logger = logging.getLogger(type(self).__name__)
        self.files: list[str] = glob(f'{folder.rstrip('/')}/**/*.xml', recursive=True)
        self.certs: dict[str, set[str]] = {}

        self.logger.info(f'Loading {len(self.files)} files in {folder}')

    def check_duplicates(self):
        self.__group_keyboxes()

        # TODO Calculate which files are the same, but for now just dump the data to the log
        duplicates = {cert_hash: list(files) for cert_hash, files in self.certs.items() if len(files) > 1}
        self.logger.info('Results: \n' + json.dumps(duplicates, indent=4))

    def __group_keyboxes(self):
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

                if cert_key not in self.certs:
                    self.certs[cert_key] = set()

                self.certs[cert_key].add(file)