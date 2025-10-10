from asyncstdlib import enumerate as a_enumerate
from base64 import b64decode
from codecs import decode
from collections.abc import AsyncGenerator
from downloaders.downloader import Downloader
from xml.etree.ElementTree import Element
import pathlib
import re
import xml.etree.ElementTree as ET


class TSupport(Downloader):
    # https://t.me/s/citraintegritytrick
    URLS = [
        # The keybox from the module (Actually just the AOSP keybox)
        #'https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/bin.tar',
        # Extra keybox files
        'https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/zipball/bin.tar',
        'https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/zipball/bin1.tar',
        'https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/zipball/blackbox0.tar',
        'https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/zipball/blackbox1.tar',
        'https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/zipball/blackbox2.tar',
        'https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/zipball/blackbox3.tar',
        'https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/zipball/blackbox4.tar',
        'https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/zipball/blackbox5.tar',
        'https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/zipball/blackbox6.tar',
        'https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/zipball/blackbox7.tar',
        'https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/zipball/blackbox8.tar',
        'https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/zipball/blackbox9.tar',
        'https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/zipball/preview.tar',
        'https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/zipball/sanctuary.tar'
    ]

    def __init__(self):
        super().__init__()

        self.keys: str | None = None

    async def get_keybox(self) -> AsyncGenerator[Element | None]:
        self.logger.info(f'There are {len(self.URLS)} keyboxes to check')

        async for idx, dl in a_enumerate(self.download_urls()):
            self.logger.info(f'Downloading encoded keybox #{idx + 1}')
            self.encoded = dl

            if len(self.encoded.strip()) > 0:
                self.logger.info(f'Building keybox xml #{idx + 1}')
                self.keys = self.decode_keybox()
                yield self.build_keybox()
            else:
                yield None

    def build_keybox(self) -> Element:
        # First, extract the metadata
        keybox_metadata = dict(re.findall(r'(TYPE|ID)=(.+)', self.keys))

        # Next, get the XML data
        keybox_keys = re.search(r'(#EC)(\s+<.+>)\s+(#RSA)(\s+<.+>)', self.keys, re.DOTALL)
        ecdsa_key = ET.fromstring(keybox_keys.group(2))
        rsa_key = ET.fromstring(keybox_keys.group(4))

        # Finally, build the XML
        keybox_xml = ET.Element('AndroidAttestation')
        ET.SubElement(keybox_xml, 'NumberOfKeyboxes').text = '1'

        keybox_element = ET.SubElement(keybox_xml, 'Keybox')
        keybox_element.set(
            'DeviceID',
            f'{'HW' if keybox_metadata['ID'] == 'Hardware Attestation' else 'SW'}'
            f'{'PVT' if keybox_metadata['TYPE'] == 'PRIVATE' else 'PUB'}'
            f'_{pathlib.Path(self.current_url).stem}'
        )
        keybox_element.append(ecdsa_key)
        keybox_element.append(rsa_key)

        return keybox_xml

    def decode_keybox(self) -> str:
        # Strip off any irrelevant data
        encoded = re.sub(r'=+.+?=.\s+', '', self.encoded, 1, re.DOTALL)

        # Some files are rot13+base64, some are just base64
        try:
            encoded = b64decode(encoded).decode('ascii')
        except UnicodeDecodeError:
            encoded = decode(encoded, 'rot_13')
            encoded = b64decode(encoded).decode('ascii')

        return encoded