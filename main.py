from downloaders.integritybox import IntegrityBox
from downloaders.trickyaddon import TrickyAddon
from downloaders.tsupport import TSupport
from downloaders.yurikey import YuriKey
from time import time
from tqdm import tqdm
from types import GeneratorType
from utils.duplicate import Duplicate
from utils.googlecheck import GoogleChecker
from xml.etree.ElementTree import ElementTree
import logging
import os


logger = logging.getLogger(__name__)

if __name__ == '__main__':
    path = 'keyboxes'
    types = ('valid', 'revoked')

    if not os.path.exists('logs'):
        os.mkdir('logs')

    if not os.path.exists(path):
        for key_type in types:
            os.makedirs(f'{path}/{key_type}')

    logging.basicConfig(filename=f'logs/keybox-downloader-{time():.0f}.log', level=logging.INFO)
    logger.info('Starting Keybox Downloader')

    checker = GoogleChecker()

    for dl in tqdm((IntegrityBox(), TrickyAddon(), TSupport(), YuriKey())):
        keybox = dl.get_keybox()
        is_generator = isinstance(keybox, GeneratorType)

        logger.info('Got keybox XML, checking revocation')

        for (idx, keybox_file) in enumerate(keybox if is_generator else (keybox,)):
            keybox_idx = idx + 1

            logger.info(f'Checking keybox #{keybox_idx:d}' if is_generator else 'Checking keybox')
            valid_keybox = checker.is_keybox_valid(keybox_file)
            save_path = f'{path}/{'valid' if valid_keybox else 'revoked'}'
            file_name = f'{save_path}/{type(dl).__name__ + (f'_{keybox_idx:d}' if is_generator else '')}.xml'

            logger.info(f'Saving keybox #{keybox_idx:d}' if is_generator else 'Saving keybox')
            xml_file = ElementTree(keybox_file)
            xml_file.write(file_name, 'unicode', True)

    logger.info('All keyboxes downloaded, comparing to find duplicates')
    dupe = Duplicate(path)

    dupe.check_duplicates()