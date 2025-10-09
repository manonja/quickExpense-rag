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
    """Types of business structures."""

    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    CORPORATION = "corporation"
    PARTNERSHIP = "partnership"


class ExpenseType(str, Enum):
    """Categories of business expenses."""

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
