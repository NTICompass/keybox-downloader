from downloaders.integritybox import IntegrityBox
from downloaders.trickyaddon import TrickyAddon
from downloaders.yurikey import YuriKey


if __name__ == '__main__':
    for dl in (IntegrityBox(), TrickyAddon(), YuriKey()):
        print(dl.get_keybox())
