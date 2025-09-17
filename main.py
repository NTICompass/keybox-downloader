from downloaders.integritybox import IntegrityBox
from downloaders.yurikey import YuriKey


if __name__ == '__main__':
    for dl in (YuriKey(),):
        print(dl.get_keybox())
