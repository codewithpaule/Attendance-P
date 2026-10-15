from datetime import date


def validate_term_dates(starts_on: date, ends_on: date) -> list[str]:
    """Validate term date boundaries. Returns list of error messages."""
    errors = []

    if starts_on >= ends_on:
        errors.append("Term start date must be before end date")

    if starts_on.year != ends_on.year:
        errors.append("Term must be within a single calendar year")

    return errors
