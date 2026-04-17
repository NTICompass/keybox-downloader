from . import Downloader
from asyncstdlib import enumerate as a_enumerate
from base64 import b64decode
from codecs import decode
from collections.abc import AsyncGenerator
from xml.etree.ElementTree import Element
import pathlib
import re
import xml.etree.ElementTree as ET


class TSupport(Downloader):
    # https://t.me/s/citraintegritytrick
    URLS = [
        # The keybox from the module (Actually just the AOSP keybox)
        #'github:Citra-Standalone/Citra-Standalone::bin.tar',
        # Extra keybox files
        'github:Citra-Standalone/Citra-Standalone::zipball/bin.tar',
        'github:Citra-Standalone/Citra-Standalone::zipball/bin1.tar',
        'github:Citra-Standalone/Citra-Standalone::zipball/blackbox0.tar',
        'github:Citra-Standalone/Citra-Standalone::zipball/blackbox1.tar',
        'github:Citra-Standalone/Citra-Standalone::zipball/blackbox2.tar',
        'github:Citra-Standalone/Citra-Standalone::zipball/blackbox3.tar',
        'github:Citra-Standalone/Citra-Standalone::zipball/blackbox4.tar',
        'github:Citra-Standalone/Citra-Standalone::zipball/blackbox5.tar',
        'github:Citra-Standalone/Citra-Standalone::zipball/blackbox6.tar',
        'github:Citra-Standalone/Citra-Standalone::zipball/blackbox7.tar',
        'github:Citra-Standalone/Citra-Standalone::zipball/blackbox8.tar',
        'github:Citra-Standalone/Citra-Standalone::zipball/blackbox9.tar',
        'github:Citra-Standalone/Citra-Standalone::zipball/preview.tar',
        'github:Citra-Standalone/Citra-Standalone::zipball/sanctuary.tar',
    ]

    keys: str

    async def get_keybox(self) -> AsyncGenerator[Element | None]:
        self.logger.info(f'There are {len(self.URLS)} keyboxes to check')

        async for idx, dl in a_enumerate(self.download_urls()):
            self.logger.info(f'Downloading encoded keybox #{idx + 1}')
            self.encoded = str(dl)

            if self.encoded is not None and len(self.encoded.strip()) > 0:
                self.logger.info(f'Building keybox xml #{idx + 1}')
                self.keys = self.decode_keybox()
                yield self.build_keybox()
            else:
                yield None

    def build_keybox(self) -> Element | None:
        # First, extract the metadata
        keybox_metadata = dict(re.findall(r'(TYPE|ID)=(.+)', self.keys))

        # Next, get the XML data
        keybox_keys = re.search(
            r'(#EC)(\s+<.+>)\s+(#RSA)(\s+<.+>)', self.keys, re.DOTALL
        )

        if keybox_keys is not None:
            ecdsa_key = ET.fromstring(keybox_keys.group(2))
            rsa_key = ET.fromstring(keybox_keys.group(4))

            # Finally, build the XML
            keybox_xml = ET.Element('AndroidAttestation')
            ET.SubElement(keybox_xml, 'NumberOfKeyboxes').text = '1'

            keybox_element = ET.SubElement(keybox_xml, 'Keybox')

            try:
                key_id = keybox_metadata["ID"]
            except KeyError:
                key_id = ''

            keybox_element.set(
                'DeviceID',
                f'{"HW" if key_id == "Hardware Attestation" else "SW"}'
                f'{"PVT" if keybox_metadata["TYPE"] == "PRIVATE" else "PUB"}'
                f'_{pathlib.Path(self.current_url.path).stem}',
            )
            keybox_element.append(ecdsa_key)
            keybox_element.append(rsa_key)

            return keybox_xml
        else:
            return None

    def decode_keybox(self) -> str:
        # Strip off any irrelevant data
        encoded = re.sub(r'=+.+?=.\s+', '', self.encoded, 1, re.DOTALL)

        # Some files are rot13+base64, some are just base64
        try:
            encoded = b64decode(encoded).decode('ascii')
        except UnicodeDecodeError:
            encoded = decode(encoded, 'rot_13')
            encoded = b64decode(encoded).decode('ascii')

        # Fix invalid XML data
        return re.sub(
            r'</Key>\s*#RSA\s*</Key>',
            '</Key>\n#RSA\n<Key algorithm="rsa">',
            encoded,
        )
