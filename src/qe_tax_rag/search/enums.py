"""Enumeration types for filtering search queries."""

from enum import Enum


class Province(str, Enum):
    """Canadian provinces and territories."""

    BC = "BC"
    AB = "AB"
    SK = "SK"
    MB = "MB"
    ON = "ON"
    QC = "QC"
    NB = "NB"
    NS = "NS"
    PE = "PE"
    NL = "NL"
    YT = "YT"
    NT = "NT"
    NU = "NU"


class BusinessType(str, Enum):
    """
    High-level CRA business structures.

    Note: This list is not exhaustive and focuses on common for-profit entities.
    """

    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    CORPORATION = "corporation"
    PARTNERSHIP = "partnership"
