from asyncstdlib import enumerate as a_enumerate
from downloaders import (
    Downloader,
    DroidWin,
    IntegrityBox,
    TrickyAddon,
    TSupport,
    YuriKey,
)
from shutil import make_archive, rmtree
from time import time
from tqdm.asyncio import tqdm_asyncio
from utils.duplicate import Duplicate
from utils.googlecheck import GoogleChecker
from xml.etree.ElementTree import ElementTree, Element
import asyncio
import logging
import os

path = 'keyboxes'
types = ('revoked', 'valid', 'aosp')
log_path = 'logs'
backup_path = 'backups'

logger = logging.getLogger(__name__)

if __name__ == '__main__':

    def make_folder(folder: str):
        if not os.path.exists(folder):
            os.mkdir(folder)

    def make_folders():
        for key_type in types:
            os.makedirs(f'{path}/{key_type}')

    make_folder(log_path)
    logging.basicConfig(
        filename=f'{log_path}/keybox-downloader-{time():.0f}.log', level=logging.INFO
    )
    logger.info('Starting Keybox Downloader')

    if not os.path.exists(path):
        make_folders()
    else:
        logger.info('Backing up existing keyboxes')

        make_folder(backup_path)
        make_archive(f'{backup_path}/keyboxes-{time():.0f}', 'zip', path)
        rmtree(path)
        make_folders()

    type KeyboxFiles = dict[str, ElementTree[Element[str] | None]]

    async def run(dl: Downloader, checker: GoogleChecker) -> KeyboxFiles:
        files: KeyboxFiles = {}

        async for idx, keybox_file in a_enumerate(dl.get_keybox()):
            keybox_idx = idx + 1

            if keybox_file is None:
                logger.info(f'Skipping empty keybox #{keybox_idx:d}')
                continue

            logger.info(f'Checking keybox #{keybox_idx:d}')
            valid_keybox = await checker.is_keybox_valid(keybox_file)

            # Check if it's the AOSP keybox before saving
            save_path = (
                f'{path}/aosp'
                if valid_keybox and checker.is_aosp_keybox(keybox_file)
                else f'{path}/{types[int(valid_keybox)]}'
            )

            logger.info(f'Saving keybox #{keybox_idx:d}')
            files[f'{save_path}/{type(dl).__name__ + f"_{keybox_idx:d}"}.xml'] = (
                ElementTree(keybox_file)
            )

        return files

    async def main(*downloaders: Downloader):
        checker = GoogleChecker()

        for task in tqdm_asyncio.as_completed(
            [asyncio.create_task(run(dl, checker)) for dl in downloaders]
        ):
            for file_name, xml_file in (await task).items():
                xml_file.write(file_name, 'unicode', True)

        await Downloader.client.aclose()

        logger.info('All keyboxes downloaded, comparing to find duplicates')
        dupe = Duplicate(path)
        dupe.check_duplicates()

    asyncio.run(main(DroidWin(), IntegrityBox(), TrickyAddon(), TSupport(), YuriKey()))
