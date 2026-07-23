# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""The downloaders are the main modules of this program, each one downloads a keybox from a different source."""

from .downloader import Downloader  # ruff: ignore[unsorted-imports]
from .alwaysstrong import AlwaysStrong
from .droidwin import DroidWin
from .fixintegrity import FixIntegrity
from .integritybox import IntegrityBox
from .play_integrityfix import PlayIntegrityFix
from .specter import Specter
from .trickyaddon import TrickyAddon
from .tsupport import TSupport
from .yurikey import YuriKey

__all__ = [
    'AlwaysStrong',
    'Downloader',
    'DroidWin',
    'FixIntegrity',
    'IntegrityBox',
    'PlayIntegrityFix',
    'Specter',
    'TSupport',
    'TrickyAddon',
    'YuriKey',
]
