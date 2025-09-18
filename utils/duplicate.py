from cryptography import x509
import glob
import logging
import xml.etree.ElementTree as ET


class Duplicate:
    def __init__(self, folder: str):
        self.logger = logging.getLogger(type(self).__name__)
        self.files: list[str] = glob.glob('{}/**/*.xml'.format(folder.rstrip('/')), recursive=True)
        self.certs: dict[str, set[str]] = {}

        self.logger.info('Loading {} files in {}'.format(len(self.files), folder))

    def check_duplicates(self):
        self.__group_keyboxes()

    def __group_keyboxes(self):
        for file in self.files:
            self.logger.info('Parsing XML file {}'.format(file))

            keybox = ET.parse(file)
            root = keybox.getroot()

            ec_certs = root.findall('.//Key[@algorithm="ecdsa"]/CertificateChain/Certificate')
            rsa_certs = root.findall('.//Key[@algorithm="rsa"]/CertificateChain/Certificate')
            self.logger.info('Found {} EC and {} RSA certs'.format(len(ec_certs), len(rsa_certs)))

            certs = x509.load_pem_x509_certificates(
                b''.join(cert_pem.text.encode() for cert_pem in ec_certs) +
                b''.join(cert_pem.text.encode() for cert_pem in rsa_certs)
            )

            for cert in certs:
                hex_serial = format(cert.serial_number, 'x').lower().lstrip('0')
                issuer_serial = {attr.value.lower() for attr in cert.issuer if attr.oid == x509.NameOID.SERIAL_NUMBER}
                cert_key = '{}_{}'.format(hex_serial, issuer_serial.pop())

                if cert_key not in self.certs:
                    self.certs[cert_key] = set()

                self.certs[cert_key].add(file)