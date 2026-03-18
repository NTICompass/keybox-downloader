from . import Downloader
from base64 import b64decode
from codecs import decode
from collections.abc import AsyncGenerator
from utils.shellvar import get_var_from_shell
from xml.etree.ElementTree import Element, ParseError
import re
import xml.etree.ElementTree as ET


def get_keybox_url(keybox_script: str) -> str:
    keybox_vars = get_var_from_shell(keybox_script, ['I', 'J', 'K', 'LOL'])
    return b64decode(
        keybox_vars['I'] + keybox_vars['J'] + keybox_vars['K'] + keybox_vars['LOL']
    ).decode('ascii')


class IntegrityBox(Downloader):
    # https://t.me/MeowDump
    URLS = [
        # Key Script
        'github:MeowDump/Integrity-Box::webroot/common_scripts/key.sh',
        # Cleanup Script
        'github:MeowDump/Integrity-Box::webroot/common_scripts/cleanup.sh',
        # Extra Keybox(es)
        'github:MeowDump/MeowDump::NullVoid/OptimusPrime',
        # https://integritybox.vercel.app/
        'github:freekeybox/mona::meow.tar',
    ]

    def __init__(self):
        super().__init__()

        self.junk: list[str] | set[str] | None = None

    async def get_keybox(self) -> AsyncGenerator[Element | None]:
        self.logger.info('Downloading keybox scripts')

        # Also download the keybox from the webapp, which is probably the same
        keybox_script, cleanup_script, encoded_keybox, web_keybox = [
            data async for data in self.download_urls()
        ]

        download_url = get_keybox_url(keybox_script)
        junk_vars = get_var_from_shell(cleanup_script, ['X'])
        self.junk = junk_vars['X'].split(',')

        keyboxes = [web_keybox]

        # Decode the keyboxes
        for encoded in ((await self.client.get(download_url)).text, encoded_keybox):
            self.encoded = encoded
            keyboxes.append(self.decode_keybox())

        # Output keyboxes as XML
        for idx, keybox in enumerate(keyboxes):
            if keybox is None:
                yield None
            else:
                # parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
                try:
                    xml = ET.fromstring(keybox)
                    keybox_id = xml.find('.//Keybox[@DeviceID]')
                    keybox_id.set(
                        'DeviceID', f'{keybox_id.get("DeviceID")} {idx + 1:d}'
                    )

                    yield xml
                except ParseError:
                    self.logger.info(f'Cannot parse "{keybox}"')
                    yield None

    def decode_keybox(self) -> str | None:
        self.logger.info('Decoding keybox xml')

        if len(self.encoded.strip()) == 0:
            return None

        encoded = self.encoded

        # Decode base64 ten times!
        for i in range(10):
            encoded = b64decode(encoded).decode('ascii')

        # Then decode the hex bytes
        encoded = bytes.fromhex(encoded).decode('utf-8')

        # Next use rot13
        encoded = decode(encoded, 'rot_13')

        # Finally remove extra "junk" from the file
        return re.sub(rf'({"|".join(self.junk)})', '', encoded)
