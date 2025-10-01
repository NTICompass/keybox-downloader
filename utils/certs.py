from collections.abc import Generator
from cryptography import x509
from cryptography.hazmat.bindings._rust import x509 as rust_x509
from xml.etree.ElementTree import Element
import logging

Certificate = rust_x509.Certificate

def get_keybox_id(keybox: Element | None) -> str | None:
    return keybox.find('.//Keybox[@DeviceID]').get('DeviceID') if keybox is not None else None

class Certs:
    cert_data: dict[int, list[Certificate]] = {}

    def __init__(self):
        self.logger = logging.getLogger(type(self).__name__)

    def load_certs(self, keybox: Element) -> int:
        cert_key = hash(keybox)

        ec_certs = keybox.findall('.//Key[@algorithm="ecdsa"]/CertificateChain/Certificate')
        rsa_certs = keybox.findall('.//Key[@algorithm="rsa"]/CertificateChain/Certificate')

        self.logger.info(f'Found {len(ec_certs)} EC and {len(rsa_certs)} RSA certs for "{get_keybox_id(keybox)}"')
        self.cert_data[cert_key] = x509.load_pem_x509_certificates(
            b''.join(cert_pem.text.encode() for cert_pem in ec_certs) +
            b''.join(cert_pem.text.encode() for cert_pem in rsa_certs)
        )

        return cert_key

    def get_certs(self, log_valid: bool = False, key: int | None = None, keybox: Element | None = None) -> Generator[Certificate]:
        cert_key = key if key is not None else hash(keybox)
        if cert_key is None:
            raise ValueError

        try:
            cert_list = self.cert_data[cert_key]
        except KeyError:
            if keybox is not None:
                cert_list = self.cert_data[self.load_certs(keybox)]
            else:
                raise ValueError

        for cert in cert_list:
            if log_valid:
                self.logger.info(
                    f'Valid between {cert.not_valid_before_utc:%a %b %d %Y, %I:%M%p} '
                    f'and {cert.not_valid_after_utc:%a %b %d %Y, %I:%M%p}'
                )
            yield cert