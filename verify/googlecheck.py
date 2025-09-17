from cryptography import x509
from cryptography.hazmat.backends import default_backend
from time import time
from typing import Optional
from xml.etree.ElementTree import Element
import requests


def get_cert_info(cert_pem: Element) -> tuple[Optional[str], Optional[str]]:
    try:
        cert = x509.load_pem_x509_certificate(cert_pem.text.encode(), default_backend())
    except ValueError:
        return None, None

    hex_serial = format(cert.serial_number, 'x').lower().lstrip('0')
    issuer_serial = {attr.value.lower() for attr in cert.issuer if attr.oid == x509.NameOID.SERIAL_NUMBER}

    return hex_serial, str(issuer_serial.pop()) if len(issuer_serial) > 0 else None

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
        for cert_pem in xml.findall('.//Key[@algorithm="ecdsa"]/CertificateChain/Certificate'):
            hex_serial, issuer_serial = get_cert_info(cert_pem)
            found = (hex_serial and hex_serial in self.revoked) or (issuer_serial and issuer_serial in self.revoked)

            if found:
                return False

        return True

