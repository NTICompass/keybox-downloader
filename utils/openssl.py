"""
If we don't have the `cryptography` module, then just call `openssl` from the command line
"""
class x509:
    def load_pem_x509_certificates(self, data: bytes) -> list[x509_cert]:
        pass

"""
To get the serial, use `openssl x509 -inform pem -noout -serial`
"""
class x509_cert:
    pass