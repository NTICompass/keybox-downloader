from downloaders.integritybox import IntegrityBox
from downloaders.trickyaddon import TrickyAddon
from downloaders.tsupport import TSupport
from downloaders.yurikey import YuriKey
from tqdm import tqdm
from verify.googlecheck import GoogleChecker
import os
import xml.etree.ElementTree as ET


def write_xml(file: str, data: str):
    with open(file, 'w', encoding='utf-8') as f:
        f.write(data)


if __name__ == '__main__':
    path = 'keyboxes'

    if not os.path.exists(path):
        os.makedirs('{}/{}'.format(path, 'valid'))
        os.makedirs('{}/{}'.format(path, 'revoked'))

    checker = GoogleChecker()

    for dl in tqdm((IntegrityBox(), TrickyAddon(), TSupport(), YuriKey())):
        keybox = dl.get_keybox()

        if isinstance(keybox, str):
            valid_keybox = checker.is_keybox_revoked(ET.fromstring(keybox))
            save_path = '{}/{}'.format(path, 'valid' if valid_keybox else 'revoked')

            write_xml('{}/{}.xml'.format(save_path, type(dl).__name__), keybox)
        else:
            for (idx, keybox_file) in enumerate(keybox):
                valid_keybox = checker.is_keybox_revoked(ET.fromstring(keybox_file))
                save_path = '{}/{}'.format(path, 'valid' if valid_keybox else 'revoked')

                write_xml('{}/{}_{}.xml'.format(save_path, type(dl).__name__, idx), keybox_file)
