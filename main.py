from downloaders.integritybox import IntegrityBox
from downloaders.trickyaddon import TrickyAddon
from downloaders.yurikey import YuriKey


if __name__ == '__main__':
    for dl in (TrickyAddon(),):
        print(dl.get_keybox())
