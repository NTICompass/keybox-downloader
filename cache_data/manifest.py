# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Save the last download date and last attestation checked date."""

from dataclasses import dataclass

from .basedata import BaseData


@dataclass
class Manifest(BaseData[float]):
    """When we last ran the program and when we last downloaded the attestation status from Google."""

    last_checked: float = 0  # Keybox downloading
    attestation_date: float = 0  # Google attestation status
