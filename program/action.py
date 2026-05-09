from asyncstdlib import enumerate as a_enumerate
from collections.abc import Generator
from datetime import datetime, timedelta
from downloaders import Downloader
from pathlib import Path
from shutil import make_archive, rmtree
from time import time
from tqdm.asyncio import tqdm_asyncio
from typing import TypedDict
from utils.duplicate import Duplicate
from utils.googlecheck import GoogleChecker
from xml.etree.ElementTree import ElementTree, Element
import __main__
import asyncio
import json
import logging


class CacheManifest(TypedDict):
    last_checked: int | float


root: Path = __main__.root
path = root / 'keyboxes'
log_path = root / 'logs'
backup_path = root / 'backups'
manifest_path = root / 'cache'
types = ('revoked', 'valid', 'aosp')
logger = logging.getLogger(__name__)
manifest: CacheManifest


def make_folders():
    path.mkdir(exist_ok=True)

    for key_type in types:
        (path / key_type).mkdir()


def init():
    log_path.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=f'{log_path}/keybox-downloader-{time():.0f}.log', level=logging.INFO
    )
    logger.info('Starting Keybox Downloader')

    # Only download once every 24hrs
    global manifest
    manifest_file = manifest_path / 'manifest.json'

    if manifest_path.exists() and manifest_file.exists():
        with open(manifest_file) as manifest_data:
            manifest = json.load(manifest_data)
            time_diff = datetime.now() - datetime.fromtimestamp(
                manifest['last_checked']
            )

            if (time_diff / timedelta(hours=1)) < 24:
                raise RuntimeError(
                    f'Last download was less than 24hrs ago: {manifest["last_checked"]}'
                )
    else:
        manifest_path.mkdir(exist_ok=True)
        manifest = {}

    if not path.exists():
        make_folders()
    else:
        logger.info('Backing up existing keyboxes')

        backup_path.mkdir(exist_ok=True)
        make_archive(f'{backup_path}/keyboxes-{time():.0f}', 'zip', path)
        rmtree(path)
        make_folders()


type KeyboxFiles = dict[str, ElementTree[Element | None]]


async def run(dl: Downloader, checker: GoogleChecker) -> KeyboxFiles:
    files: KeyboxFiles = {}

    async for idx, keybox_file in a_enumerate(dl()):
        keybox_idx = idx + 1

        if keybox_file is None:
            logger.info(f'Skipping empty keybox #{keybox_idx:d}')
            continue

        logger.info(f'Checking keybox #{keybox_idx:d}')

        # Fix certs, remove excess new lines
        for cert in keybox_file.iterfind('.//Keybox//Certificate[@format="pem"]'):
            if cert.text:
                # From: https://stackoverflow.com/a/17610612
                cert.text = '\n'.join(
                    [ll.rstrip() for ll in cert.text.splitlines() if ll.strip()]
                )

        # Probably fix the private keys, too
        for key in keybox_file.iterfind('.//Keybox//PrivateKey[@format="pem"]'):
            if key.text:
                key.text = '\n'.join(
                    [ll.rstrip() for ll in key.text.splitlines() if ll.strip()]
                )

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


async def go(*downloaders: Downloader):
    try:
        init()
    except RuntimeError as e:
        logger.info(e)
    else:
        checker = GoogleChecker()

        for task in tqdm_asyncio.as_completed(
            [asyncio.create_task(run(dl, checker)) for dl in downloaders]
        ):
            for file_name, xml_file in (await task).items():
                xml_file.write(file_name, 'unicode', True)

        await Downloader.client.aclose()

        logger.info('All keyboxes downloaded, comparing to find duplicates')
        dupe = Duplicate(str(path))
        dupe.check_duplicates()

        with open(f'{manifest_path}/manifest.json', 'w') as manifest_data:
            global manifest

            manifest['last_checked'] = datetime.now().timestamp()
            json.dump(manifest, manifest_data)


def get_downloaders() -> Generator[Downloader]:
    return (cls() for cls in Downloader.registry)
