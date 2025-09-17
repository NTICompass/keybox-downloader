from downloaders.integritybox import IntegrityBox
from downloaders.trickyaddon import TrickyAddon
from downloaders.yurikey import YuriKey
import os


if __name__ == '__main__':
    path = 'keyboxes'
    if not os.path.exists(path):
        os.mkdir(path)

    for dl in (IntegrityBox(), TrickyAddon(), YuriKey()):
        keybox = dl.get_keybox()

        with open('{}/{}.xml'.format(path, type(dl).__name__), 'w', encoding='utf-8') as f:
            f.write(keybox)
