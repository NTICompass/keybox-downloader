from cryptography import x509
from time import time
from typing import Generator, Optional
from xml.etree.ElementTree import Element
import requests


def get_certs_info(certs: list[bytes]) -> Generator[tuple[Optional[str], Optional[str]]]:
    try:
        for cert in x509.load_pem_x509_certificates(b''.join(certs)):
            hex_serial = format(cert.serial_number, 'x').lower().lstrip('0')
            issuer_serial = {attr.value.lower() for attr in cert.issuer if attr.oid == x509.NameOID.SERIAL_NUMBER}

            yield hex_serial, str(issuer_serial.pop()) if len(issuer_serial) > 0 else None
    except ValueError:
        for x in range(len(certs)):
            yield None, None

"""
Thanks to https://github.com/Ante0/YetAnotherKeyboxChecker
"""
class GoogleChecker:
    URL = 'https://android.googleapis.com/attestation/status?' + str(int(time()))

    def __init__(self):
        keybox_status = requests.get(self.URL, headers={
            'Accept-Encoding': 'br, gzip',
            'Cache-Control': 'no-cache',
        }).json()

        self.revoked: set[str] = {key for (key, status) in keybox_status['entries'].items() if status['status'] == 'REVOKED'}

    def is_keybox_valid(self, xml: Element) -> bool:
        xml_certs = xml.findall('.//Key[@algorithm="ecdsa"]/CertificateChain/Certificate')

        for (hex_serial, issuer_serial) in get_certs_info([cert_pem.text.encode() for cert_pem in xml_certs]):
            found = (hex_serial and hex_serial in self.revoked) or (issuer_serial and issuer_serial in self.revoked)

            if found:
                return False

        return True

