"""A point-in-time view must hold only what was public by its date, and say how availability is known."""

from datetime import date

from brdo.models import DocumentDate
from brdo.pit import as_of, available_from
from brdo.status import derive_status
from brdo.vocab import CoverageStatus, DateBasis, DocumentDateKind
from tests.conftest import ISIN_LISTED, QUARTER, make_document


def _dated(kind: DocumentDateKind, day: date, basis: DateBasis) -> DocumentDate:
    return DocumentDate(kind=kind, value=day, basis=basis)


def test_a_publication_date_is_preferred_to_the_documents_own_date():
    document = make_document(
        dates=[
            _dated(DocumentDateKind.DATED, date(2026, 7, 2), DateBasis.STATED_IN_DOCUMENT),
            _dated(DocumentDateKind.PUBLISHED, date(2026, 8, 3), DateBasis.HTTP_LAST_MODIFIED),
        ]
    )
    assert available_from(document) == (date(2026, 8, 3), "http_last_modified")


def test_a_documents_own_date_is_only_a_lower_bound():
    document = make_document(dates=[_dated(DocumentDateKind.DATED, date(2026, 7, 2), DateBasis.STATED_IN_DOCUMENT)])
    assert available_from(document) == (date(2026, 7, 2), "not before its own date")


def test_a_document_of_unknown_availability_is_left_out(dataset):
    assert available_from(dataset.documents["report-q1"]) == (None, "unknown")
    assert not as_of(dataset, date(2030, 1, 1)).breach_reports


def test_a_report_published_after_the_date_does_not_count(dataset):
    published = _dated(DocumentDateKind.PUBLISHED, date(2026, 9, 13), DateBasis.HTTP_LAST_MODIFIED)
    dataset.documents["report-q1"] = make_document(dates=[published])
    before, after = as_of(dataset, date(2026, 9, 12)), as_of(dataset, date(2026, 9, 13))
    assert derive_status(before, ISIN_LISTED, QUARTER.end).status is not CoverageStatus.REPORTED_BREACH
    assert derive_status(after, ISIN_LISTED, QUARTER.end).status is CoverageStatus.REPORTED_BREACH
