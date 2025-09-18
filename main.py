from downloaders.integritybox import IntegrityBox
from downloaders.trickyaddon import TrickyAddon
from downloaders.tsupport import TSupport
from downloaders.yurikey import YuriKey
from time import time
from tqdm import tqdm
from types import GeneratorType
from verify.googlecheck import GoogleChecker
from xml.etree.ElementTree import ElementTree
import logging
import os


logger = logging.getLogger(__name__)

if __name__ == '__main__':
    path = 'keyboxes'

    if not os.path.exists('logs'):
        os.mkdir('logs')

    if not os.path.exists(path):
        os.makedirs('{}/{}'.format(path, 'valid'))
        os.makedirs('{}/{}'.format(path, 'revoked'))

    logging.basicConfig(filename='logs/keybox-downloader-{}.log'.format(int(time())), level=logging.INFO)
    logger.info('Starting Keybox Downloader')

    checker = GoogleChecker()

    for dl in tqdm((IntegrityBox(), TrickyAddon(), TSupport(), YuriKey())):
        keybox = dl.get_keybox()
        is_generator = isinstance(keybox, GeneratorType)

        logger.info('Got keybox XML, checking revocation')

        for (idx, keybox_file) in enumerate(keybox if is_generator else (keybox,)):
            logger.info('Checking keybox #{}'.format(idx + 1) if is_generator else 'Checking keybox')
            valid_keybox = checker.is_keybox_valid(keybox_file)
            save_path = '{}/{}'.format(path, 'valid' if valid_keybox else 'revoked')
            file_name = '{}/{}.xml'.format(save_path, type(dl).__name__ + ('_{}'.format(idx + 1) if is_generator else ''))

            logger.info('Saving keybox #{}'.format(idx + 1) if is_generator else 'Saving keybox')
            xml_file = ElementTree(keybox_file)
            xml_file.write(file_name, 'unicode', True)