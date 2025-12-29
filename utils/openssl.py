import re

"""
If we don't have the `cryptography` module, then just call `openssl` from the command line
"""
class x509:
    BEGIN = '-----BEGIN CERTIFICATE-----'
    END = '-----END CERTIFICATE-----'

    def load_pem_x509_certificates(self, data: bytes) -> list[x509_cert]:
        return [x509_cert(cert) for cert in re.findall(rf'{self.BEGIN}(.+?){self.END}', data.decode('ascii'))]

"""
To get the serial, use `openssl x509 -inform pem -noout -serial`
"""
class x509_cert:
    def __init__(self, cert: str):
        pass