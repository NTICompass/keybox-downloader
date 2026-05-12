from enum import StrEnum, auto


class KeyType(StrEnum):
    VALID = auto()
    SEMI_VALID = auto()
    REVOKED = auto()
    AOSP = auto()
