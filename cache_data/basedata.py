# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""`BaseData` for all JSON cache files."""

import json
from dataclasses import dataclass, field, fields
from json import JSONDecodeError
from pathlib import Path
from typing import ClassVar

import __main__


@dataclass
class BaseData[T]:
    """Override and add your options to save as a JSON file.

    Everywhere else, I am using `anyio.Path`, but in here,
    we may be inside `Downloader.__init_subclass__` which happens BEFORE the event loop.
    """

    _loaded = False

    _root: ClassVar[Path] = Path(__main__.exe_root)
    _manifest_path: ClassVar[Path] = _root / 'cache'
    _manifest_json = 'manifest.json'
    _manifest_file: Path = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the JSON file when loading child classes."""
        self._manifest_file = self._manifest_path / self._manifest_json

        self._manifest_path.mkdir(exist_ok=True)
        self._manifest_file.touch(exist_ok=True)

        with self._manifest_file.open(encoding='utf-8') as file:
            try:
                for k, v in json.load(file).items():
                    object.__setattr__(self, k, v)
            except JSONDecodeError:
                pass
            finally:
                self._loaded = True

    def __setattr__(self, name: str, value: T) -> None:
        """Keys starting with an `_` are "private", the rest are saved into the JSON."""
        super().__setattr__(name, value)

        if not name.startswith('_') and self._loaded:
            self.save()

    def save(self) -> None:
        """Write the saved data into a JSON file."""
        with self._manifest_file.open('w', encoding='utf-8') as file:
            json.dump({f.name: getattr(self, f.name) for f in fields(self) if not f.name.startswith('_')}, file)
