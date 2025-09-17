from base64 import b64decode
from codecs import decode
from downloaders.downloader import Downloader
import re
import requests
import uuid
import xml.etree.ElementTree as ET


class TSupport(Downloader):
    # https://t.me/s/citraintegritytrick
    URL='https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/bin.tar'

    def get_keybox(self) -> str:
        self.encoded = requests.get(self.URL).text
        return self.__build_keybox()

    def __build_keybox(self) -> str:
        encoded = self.encoded

        # First we need to rot13
        encoded = decode(encoded, 'rot_13')

        # Then base64 decode
        encoded = b64decode(encoded).decode('ascii')

        # This isn't the full keybox file, we need to build it

        # First, extract the metadata
        keybox_metadata = dict(re.findall(r'(TYPE|ID)=(.+)', encoded))

        # Next, get the XML data
        keybox_keys = re.search(r'(#EC)(\s+<.+>)\s+(#RSA)(\s+<.+>)', encoded, re.DOTALL)
        ecdsa_key = ET.fromstring(keybox_keys.group(2))
        rsa_key = ET.fromstring(keybox_keys.group(4))

        # Finally, build the XML
        keybox_xml = ET.Element('AndroidAttestation')
        ET.SubElement(keybox_xml, 'NumberOfKeyboxes').text = '1'

        keybox_element = ET.SubElement(keybox_xml, 'Keybox')
        keybox_element.set('DeviceID', '{}{}_{}'.format(
            'HW' if keybox_metadata['ID'] == 'Hardware Attestation' else 'SW',
            'PVT' if keybox_metadata['TYPE'] == 'PRIVATE' else 'PUB',
            str(uuid.uuid4()).split('-')[0]
        ))
        keybox_element.append(ecdsa_key)
        keybox_element.append(rsa_key)

        return ET.tostring(keybox_xml, encoding='unicode')