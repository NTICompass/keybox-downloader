from collections.abc import Generator
from cryptography import x509
from cryptography.x509.base import Certificate
from xml.etree.ElementTree import Element
import logging


def get_keybox_id(keybox: Element | None) -> str | None:
    if keybox is None:
        return None

    device = keybox.find('.//Keybox[@DeviceID]')
    return device.get('DeviceID') if device is not None else None


class Certs:
    cert_data: dict[int, list[Certificate]] = {}
    cert_counts: dict[int, tuple[int, int]] = {}

    def __init__(self):
        self.logger = logging.getLogger(type(self).__name__)

    def load_certs(self, keybox: Element) -> int:
        cert_key = hash(keybox)

        ec_certs = keybox.findall(
            './/Key[@algorithm="ecdsa"]/CertificateChain/Certificate'
        )
        rsa_certs = keybox.findall(
            './/Key[@algorithm="rsa"]/CertificateChain/Certificate'
        )

        self.cert_counts[cert_key] = (len(ec_certs), len(rsa_certs))
        self.logger.info(
            f'Found {self.cert_counts[cert_key][0]} EC and {self.cert_counts[cert_key][1]} RSA certs for "{get_keybox_id(keybox)}"'
        )

        try:
            self.cert_data[cert_key] = x509.load_pem_x509_certificates(
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
            return 0

        return cert_key

    def get_certs(
        self,
        log_valid: bool = False,
        key: int | None = None,
        keybox: Element | None = None,
    ) -> Generator[Certificate]:
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

    def get_counts(
        self, key: int | None = None, keybox: Element | None = None
    ) -> tuple[int, int]:
        cert_key = key if key is not None else hash(keybox)
        if cert_key is None:
            raise ValueError

        return self.cert_counts[cert_key]
