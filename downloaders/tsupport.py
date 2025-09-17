from base64 import b64decode
from codecs import decode
from downloaders.downloader import Downloader
from typing import Optional
from utils.shellvar import get_var_from_shell
from zipfile import ZipFile
import io
import re
import requests
import uuid
import xml.etree.ElementTree as ET


class TSupport(Downloader):
    # https://t.me/s/citraintegritytrick
    URL='https://github.com/Citra-Standalone/Citra-Standalone/raw/refs/heads/main/release.json'

    def __init__(self):
        super().__init__()
        self.module_zip: Optional[ZipFile] = None

    def get_keybox(self) -> str:
        self.module_zip = self.__get_module_zip()
        self.encoded = self.__get_encoded_keybox()
        return self.__build_keybox()

    def __get_module_zip(self) -> ZipFile:
        update_file = requests.get(self.URL).json()
        file = io.BytesIO(requests.get(update_file['zipUrl']).content)
        return ZipFile(file)

    def __get_encoded_keybox(self) -> str:
        with self.module_zip as zipModule:
            keybox_script = zipModule.read('core/key.sh').decode('ascii')

        keybox_vars = get_var_from_shell(keybox_script, ['URL'])
        return requests.get(keybox_vars['URL']).text

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