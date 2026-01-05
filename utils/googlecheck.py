from downloaders.downloader import Downloader
from time import time
from utils.certs import Certs
from xml.etree.ElementTree import Element

try:
    from cryptography import x509
except ImportError:
    from .openssl import x509

"""
Thanks to https://github.com/Ante0/YetAnotherKeyboxChecker
and https://github.com/Transwarpcom/Check-Keybox-Certificate-Revocation-Status

Also see https://developer.android.com/privacy-and-security/security-key-attestation
"""


class GoogleChecker(Certs):
    URL = f'https://android.googleapis.com/attestation/status?{time():.0f}'

    def __init__(self):
        super().__init__()
        self.revoked: set[str] | None = None
        self.status_list: dict | None = None

    async def is_keybox_valid(self, xml: Element) -> bool:
        if self.status_list is None:
            self.logger.info('Downloading revoked keybox list from Google')
            self.status_list = (
                await Downloader.client.get(self.URL)
            ).json()

            self.revoked = {
                key
                for key, status in self.status_list['entries'].items()
                if status['status'] == 'REVOKED'
            }

        for cert in self.get_certs(log_valid=True, key=self.load_certs(xml)):
            issuer_serial = {
                attr.value.lower()
                for attr in cert.issuer
                if attr.oid == x509.NameOID.SERIAL_NUMBER
            }
            parsed_serials = (
                f'{cert.serial_number:x}',
                str(issuer_serial.pop()) if len(issuer_serial) > 0 else None,
            )

            self.logger.info('Parsed cert {}, issuer {}'.format(*parsed_serials))

            found = (parsed_serials[0] and parsed_serials[0] in self.revoked) or (
                parsed_serials[1] and parsed_serials[1] in self.revoked
            )
            self.logger.info('Cert is revoked' if found else 'Cert is valid')

            if found:
                return False

        return True
