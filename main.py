from downloaders.integritybox import IntegrityBox
from downloaders.trickyaddon import TrickyAddon
from downloaders.tsupport import TSupport
from downloaders.yurikey import YuriKey
from tqdm import tqdm
from types import GeneratorType
from verify.googlecheck import GoogleChecker
from xml.etree.ElementTree import ElementTree
import os


if __name__ == '__main__':
    path = 'keyboxes'

    if not os.path.exists(path):
        os.makedirs('{}/{}'.format(path, 'valid'))
        os.makedirs('{}/{}'.format(path, 'revoked'))

    checker = GoogleChecker()

    for dl in tqdm((IntegrityBox(), TrickyAddon(), TSupport(), YuriKey())):
        keybox = dl.get_keybox()
        is_generator = isinstance(keybox, GeneratorType)

        for (idx, keybox_file) in enumerate(keybox if is_generator else (keybox,)):
            valid_keybox = checker.is_keybox_valid(keybox_file)
            save_path = '{}/{}'.format(path, 'valid' if valid_keybox else 'revoked')
            file_name = '{}/{}.xml'.format(save_path, type(dl).__name__ + ('_{}'.format(idx) if is_generator else ''))

            xml_file = ElementTree(keybox_file)
            xml_file.write(file_name, 'unicode', True)