"""Helpers for building iOS locators from text values."""


def predicate_literal(value: str) -> str:
    """Quote a text value for use in an iOS predicate.

    Args:
        value: Literal text, which may contain quotes or backslashes.

    Returns:
        An escaped, single-quoted predicate string literal.
    """
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
