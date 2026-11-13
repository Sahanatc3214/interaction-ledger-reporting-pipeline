"""
Validation and normalization functions for Assignment A.

These functions convert messy input values into a consistent format.
"""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def normalize_string(value):
    """Trim whitespace from a string."""
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def normalize_phone(value):
    """
    Normalize an Indian mobile number.

    Accepted examples:
        9876543210
        +919876543210
        91-9876543210
        09876543210

    Returns:
        +919876543210

    Raises:
        ValueError if the phone number is invalid.
    """
    value = normalize_string(value)

    if value is None:
        return None

    # Keep only digits.
    digits = re.sub(r"\D", "", value)

    # Remove Indian country code.
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]

    # Remove leading zero.
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    # Must be a valid 10-digit Indian mobile number.
    if len(digits) != 10 or digits[0] not in "6789":
        raise ValueError("invalid_phone")

    return "+91" + digits


def normalize_date(value):
    """
    Convert supported date formats into YYYY-MM-DD.

    Supported formats:
        YYYY-MM-DD
        DD/MM/YYYY
        DD-MM-YYYY
        DD-Mon-YYYY

    Example:
        21-11-2026 -> 2026-11-21
    """
    value = normalize_string(value)

    if value is None:
        return None

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d-%b-%Y",
    ]

    for date_format in formats:
        try:
            parsed_date = datetime.strptime(value, date_format)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ValueError("invalid_date")


def normalize_decimal(value):
    """
    Normalize an amount into a decimal string with two decimal places.

    Supported examples:
        ₹27,554
        Rs 27554
        Rs. 27,554
        INR 25301.4
        6850

    Negative values and invalid comma grouping are rejected.
    """
    value = normalize_string(value)

    if value is None:
        return None

    # Remove an optional currency prefix.
    value = re.sub(
        r"^(?:₹|Rs\.?|INR)\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )

    value = value.strip()

    # Validate number format and comma grouping.
    number_pattern = r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?"

    if not re.fullmatch(number_pattern, value):
        raise ValueError("invalid_decimal")

    try:
        amount = Decimal(value.replace(",", ""))

        if amount < 0:
            raise ValueError("invalid_decimal")

        amount = amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        return format(amount, ".2f")

    except InvalidOperation:
        raise ValueError("invalid_decimal")


def normalize_enum(value, allowed_values):
    """
    Match a value against allowed enum values, ignoring case.

    Example:
        "Hindi" is NOT automatically converted to "hi".
        " HI " becomes "hi" when "hi" is an allowed value.
    """
    value = normalize_string(value)

    if value is None:
        return None

    allowed = {item.lower() for item in allowed_values}
    normalized = value.lower()

    if normalized not in allowed:
        raise ValueError("invalid_enum")

    return normalized


def normalize_value(value, field):
    """
    Normalize a value according to its schema field type.

    The field argument is one field dictionary from the workflow JSON.
    """
    field_type = field["type"]

    if field_type == "string":
        return normalize_string(value)

    if field_type == "phone":
        return normalize_phone(value)

    if field_type == "date":
        return normalize_date(value)

    if field_type == "decimal":
        return normalize_decimal(value)

    if field_type == "enum":
        return normalize_enum(value, field["values"])

    raise ValueError(f"Unsupported field type: {field_type}")