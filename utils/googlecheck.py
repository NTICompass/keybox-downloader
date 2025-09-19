from cryptography import x509
from time import time
from typing import Generator, Optional
from xml.etree.ElementTree import Element
import logging
import requests


"""
Thanks to https://github.com/Ante0/YetAnotherKeyboxChecker
and https://github.com/Transwarpcom/Check-Keybox-Certificate-Revocation-Status

Also see https://developer.android.com/privacy-and-security/security-key-attestation
"""
class GoogleChecker:
    URL = f'https://android.googleapis.com/attestation/status?{time():.0f}'

    def __init__(self):
        self.logger = logging.getLogger(type(self).__name__)

        self.logger.info('Downloading revoked keybox list from Google')
        keybox_status = requests.get(self.URL, headers={
            'Accept-Encoding': 'br, gzip',
            'Cache-Control': 'no-cache',
        }).json()

        self.revoked: set[str] = {key for key, status in keybox_status['entries'].items() if status['status'] == 'REVOKED'}

    def is_keybox_valid(self, xml: Element) -> bool:
        ec_certs = xml.findall('.//Key[@algorithm="ecdsa"]/CertificateChain/Certificate')
        rsa_certs = xml.findall('.//Key[@algorithm="rsa"]/CertificateChain/Certificate')
        self.logger.info(f'Found {len(ec_certs)} EC and {len(rsa_certs)} RSA certs')

        for hex_serial, issuer_serial in self.get_certs_info([ec_certs[0].text.encode(), rsa_certs[0].text.encode()]):
            found = (hex_serial and hex_serial in self.revoked) or (issuer_serial and issuer_serial in self.revoked)
            self.logger.info('Cert is revoked' if found else 'Cert is valid')

            if found:
                return False

        return True

    def get_certs_info(self, certs: list[bytes]) -> Generator[tuple[Optional[str], Optional[str]]]:
        try:
            self.logger.info(f'Loading {len(certs)} certs')

            # Load each cert individually, since `load_pem_x509_certificates` will crash if ANY are invalid
            for cert in (x509.load_pem_x509_certificate(cert_pem) for cert_pem in certs):
                hex_serial = f'{cert.serial_number:x}'
                issuer_serial = {attr.value.lower() for attr in cert.issuer if attr.oid == x509.NameOID.SERIAL_NUMBER}

                parsed_serials = (hex_serial, str(issuer_serial.pop()) if len(issuer_serial) > 0 else None)
                self.logger.info('Parsed cert {}, issuer {}'.format(*parsed_serials))

                yield parsed_serials
        except ValueError:
            self.logger.info('Could not parse cert')
            yield None, None