from downloaders.integritybox import IntegrityBox
from downloaders.trickyaddon import TrickyAddon
from downloaders.tsupport import TSupport
from downloaders.yurikey import YuriKey
import os
from tqdm import tqdm


def write_xml(file: str, data: str):
    with open(file, 'w', encoding='utf-8') as f:
        f.write(data)


if __name__ == '__main__':
    path = 'keyboxes'
    if not os.path.exists(path):
        os.mkdir(path)

    for dl in tqdm((IntegrityBox(), TrickyAddon(), TSupport(), YuriKey())):
        keybox = dl.get_keybox()

        if isinstance(keybox, str):
            write_xml('{}/{}.xml'.format(path, type(dl).__name__), keybox)
        else:
            for (idx, keybox_file) in enumerate(keybox):
                write_xml('{}/{}_{}.xml'.format(path, type(dl).__name__, idx), keybox_file)
