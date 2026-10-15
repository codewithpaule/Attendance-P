from datetime import date

from apps.academics.domain.term import validate_term_dates


def test_validate_term_dates_valid():
    starts_on = date(2024, 1, 15)
    ends_on = date(2024, 5, 15)
    errors = validate_term_dates(starts_on, ends_on)
    assert errors == []


def test_validate_term_dates_start_after_end():
    starts_on = date(2024, 5, 15)
    ends_on = date(2024, 1, 15)
    errors = validate_term_dates(starts_on, ends_on)
    assert len(errors) == 1
    assert "before end date" in errors[0]


def test_validate_term_dates_different_years():
    starts_on = date(2023, 12, 1)
    ends_on = date(2024, 1, 31)
    errors = validate_term_dates(starts_on, ends_on)
    assert len(errors) == 1
    assert "single calendar year" in errors[0]
