from asyncstdlib import enumerate as a_enumerate
from downloaders.downloader import Downloader
from downloaders.integritybox import IntegrityBox
from downloaders.trickyaddon import TrickyAddon
from downloaders.tsupport import TSupport
from downloaders.yurikey import YuriKey
from shutil import make_archive, rmtree
from time import time
from tqdm import tqdm
from types import AsyncGeneratorType
from utils.duplicate import Duplicate
from utils.googlecheck import GoogleChecker
from xml.etree.ElementTree import ElementTree
import asyncio
import logging
import os

path = 'keyboxes'
types = ('revoked', 'valid')
log_path = 'logs'
backup_path = 'backups'

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    def make_folder(folder: str):
        if not os.path.exists(folder):
            os.mkdir(folder)

    def make_folders():
        for key_type in types:
            os.makedirs(f'{path}/{key_type}')

    make_folder(log_path)
    logging.basicConfig(filename=f'{log_path}/keybox-downloader-{time():.0f}.log', level=logging.INFO)
    logger.info('Starting Keybox Downloader')

    if not os.path.exists(path):
        make_folders()
    else:
        logger.info('Backing up existing keyboxes')

        make_folder(backup_path)
        make_archive(f'{backup_path}/keyboxes-{time():.0f}', 'zip', path)
        rmtree(path)
        make_folders()

    async def main(*downloaders: Downloader):
        checker = GoogleChecker()

        for dl in tqdm(downloaders):
            keybox = dl.get_keybox()
            is_generator = isinstance(keybox, AsyncGeneratorType)

            logger.info('Got keybox XML, checking revocation')

            async for idx, keybox_file in a_enumerate(keybox if is_generator else (await keybox,)):
                keybox_idx = idx + 1

                logger.info(f'Checking keybox #{keybox_idx:d}' if is_generator else 'Checking keybox')
                valid_keybox = await checker.is_keybox_valid(keybox_file)
                save_path = f'{path}/{types[int(valid_keybox)]}'
                file_name = f'{save_path}/{type(dl).__name__ + (f'_{keybox_idx:d}' if is_generator else '')}.xml'

                logger.info(f'Saving keybox #{keybox_idx:d}' if is_generator else 'Saving keybox')
                xml_file = ElementTree(keybox_file)
                xml_file.write(file_name, 'unicode', True)

        await Downloader.client.aclose()

        logger.info('All keyboxes downloaded, comparing to find duplicates')
        dupe = Duplicate(path)
        dupe.check_duplicates()

    asyncio.run(main(IntegrityBox(), TrickyAddon(), TSupport(), YuriKey()))
