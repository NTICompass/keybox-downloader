from downloaders.integritybox import IntegrityBox


if __name__ == '__main__':
    for dl in (IntegrityBox(),):
        print(dl.get_keybox())
