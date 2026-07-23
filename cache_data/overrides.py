# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Allow saving which downloaders are ran."""

from dataclasses import dataclass, field

from .basedata import BaseData


@dataclass
class Overrides[T: type](BaseData[T]):
    """Allows toggling each `Downloader` class on and off (overrides its `enabled` property)."""

    enabled: dict[str, bool] = field(default_factory=dict)
    _manifest_json = 'overrides.json'

    def toggle(self, cls: T, *, value: bool, save: bool = True) -> None:
        """Toggle the specific class on or off."""
        self.enabled[cls.__name__] = value

        if save:
            self.save()

    def is_enabled(self, cls: T) -> bool | None:
        """Check if the selected class is enabled.

        Args:
            cls: The `Downloader` subclass to check

        Returns:
            If that class has been overridden here (bool if so, None otherwise)

        """
        return self.enabled.get(cls.__name__, None)
