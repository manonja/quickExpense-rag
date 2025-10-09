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


class ExpenseType(str, Enum):
    """
    High-level business expense categories for metadata filtering.

    Note: The semantic search query handles specific nuances.
    """

    MEALS = "meals"
    TRAVEL = "travel"
    VEHICLE = "vehicle"
    HOME_OFFICE = "home_office"
    ADVERTISING = "advertising"
    INSURANCE = "insurance"
    PROFESSIONAL_FEES = "professional_fees"
    SUPPLIES = "supplies"
    UTILITIES = "utilities"
    RENT = "rent"

    @classmethod
    def all_values(cls) -> list[str]:
        """
        Return all expense type values as a list of strings.

        This method serves as the single source of truth for the canonical
        list of expense types, used to populate the expense_types table.

        Returns:
            List of all expense type string values

        """
        return [e.value for e in cls]
