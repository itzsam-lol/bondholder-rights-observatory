"""Deriving, for each ISIN and reporting period, what the reviewed record says about breaches.

The derivation is mechanical and conservative. It reports what the reviewed
documents state, never what probably happened. An instrument that is absent
from its trustee's report is ``no_report_found``, never "compliant", and the
``basis`` records exactly which kind of absence was observed.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from brdo.models import BreachItem, BreachReport, ComplianceStatement
from brdo.store import Dataset
from brdo.vocab import (
    CovenantCategory,
    CoverageStatus,
    InstrumentProperty,
    NoticeKind,
    SearchOutcome,
    SearchPurpose,
    StatementScope,
)


class StatusBasis(StrEnum):
    LISTED_IN_CURRENT_VERSION = "listed_in_current_version"
    NAMED_IN_TRUSTEE_NOTICE = "named_in_trustee_notice"
    LISTED_AS_CARRIED_OVER = "listed_as_carried_over"
    LISTED_ONLY_IN_EARLIER_VERSION = "listed_only_in_earlier_version"
    LISTING_DEPENDS_ON_LAYOUT = "listing_depends_on_layout"
    EXPLICIT_STATEMENT = "explicit_statement"
    STATEMENTS_DISAGREE = "statements_disagree"
    ISSUER_NAMED_AS_NO_INFORMATION = "issuer_named_as_no_information"
    NOT_LISTED_IN_TRUSTEE_REPORT = "not_listed_in_trustee_report"
    TRUSTEE_REPORT_IS_NIL = "trustee_report_is_nil"
    TRUSTEE_REPORT_INCOMPLETELY_TRANSCRIBED = "trustee_report_incompletely_transcribed"
    TRUSTEE_REPORT_NOT_ACCESSIBLE = "trustee_report_not_accessible"
    TRUSTEE_REPORT_NOT_LOCATED = "trustee_report_not_located"
    TRUSTEE_REPORT_NOT_SEARCHED = "trustee_report_not_searched"
    TRUSTEE_NOT_ESTABLISHED = "trustee_not_established"
    TRUSTEE_UNKNOWN = "trustee_unknown"


@dataclass(frozen=True)
class InstrumentStatus:
    isin: str
    period_end: date
    status: CoverageStatus
    basis: StatusBasis
    documents: tuple[str, ...] = ()


def current_versions(reports: list[BreachReport], dataset: Dataset) -> list[BreachReport]:
    """Reports not superseded by another report in the same list."""
    superseded = {earlier for report in reports for earlier in dataset.documents[report.document].supersedes}
    return [report for report in reports if report.document not in superseded]


def _lists(report: BreachReport, isin: str) -> tuple[bool, bool]:
    """Whether ``report`` lists ``isin``, and whether every listing is layout-dependent."""
    items = [item for row in report.rows for item in row.items if isin in item.isins]
    return bool(items), bool(items) and all(item.assignment_uncertain for item in items)


def trustees_claimed(dataset: Dataset, isin: str) -> set[str]:
    instrument = dataset.instruments[isin]
    return {str(claim.value) for claim in instrument.claims if claim.property is InstrumentProperty.DEBENTURE_TRUSTEE}


def addresses(statement: ComplianceStatement, items: Iterable[BreachItem]) -> bool:
    """Whether a statement's stated scope reaches at least one of the listed covenants."""
    if statement.scope is StatementScope.ALL_COVENANTS:
        return True
    return any(item.category is CovenantCategory.FINANCIAL for item in items)


def derive_status(dataset: Dataset, isin: str, period_end: date) -> InstrumentStatus:
    def result(status: CoverageStatus, basis: StatusBasis, documents: Iterable[str] = ()) -> InstrumentStatus:
        return InstrumentStatus(isin, period_end, status, basis, tuple(sorted(set(documents))))

    reports = [report for report in dataset.breach_reports.values() if report.period.end == period_end]
    current = current_versions(reports, dataset)
    listed_now = [(report, _lists(report, isin)) for report in current]
    listed_now = [(report, uncertain) for report, (listed, uncertain) in listed_now if listed]
    listed_earlier = [report for report in reports if report not in current and _lists(report, isin)[0]]

    statements = [
        statement
        for statement in dataset.compliance_statements.values()
        if isin in statement.instruments and statement.period.start <= period_end <= statement.period.end
    ]
    says_no_breach = [statement for statement in statements if not statement.breach_stated]

    if listed_now:
        documents = [report.document for report, _ in listed_now]
        rows = [row for report, _ in listed_now for row in report.rows if isin in row.isins]
        listed_items = [item for row in rows for item in row.items if isin in item.isins]
        contradicting = [statement for statement in says_no_breach if addresses(statement, listed_items)]
        if contradicting:
            return result(
                CoverageStatus.CONFLICTING,
                StatusBasis.STATEMENTS_DISAGREE,
                documents + [statement.document for statement in contradicting],
            )
        if all(uncertain for _, uncertain in listed_now):
            return result(CoverageStatus.AMBIGUOUS, StatusBasis.LISTING_DEPENDS_ON_LAYOUT, documents)
        if all(row.carried_over_from for row in rows):
            return result(CoverageStatus.REPORTED_BREACH, StatusBasis.LISTED_AS_CARRIED_OVER, documents)
        return result(CoverageStatus.REPORTED_BREACH, StatusBasis.LISTED_IN_CURRENT_VERSION, documents)
    if listed_earlier:
        return result(
            CoverageStatus.CONFLICTING,
            StatusBasis.LISTED_ONLY_IN_EARLIER_VERSION,
            [report.document for report in listed_earlier],
        )
    notices = [
        notice
        for notice in dataset.breach_notices.values()
        if notice.kind is NoticeKind.BREACH and notice.period_end == period_end and isin in notice.isins
    ]
    if notices:
        return result(
            CoverageStatus.REPORTED_BREACH, StatusBasis.NAMED_IN_TRUSTEE_NOTICE, [n.document for n in notices]
        )
    if statements:
        documents = [statement.document for statement in statements]
        if len(says_no_breach) == len(statements):
            return result(CoverageStatus.REPORTED_NO_BREACH, StatusBasis.EXPLICIT_STATEMENT, documents)
        if says_no_breach:
            return result(CoverageStatus.CONFLICTING, StatusBasis.STATEMENTS_DISAGREE, documents)
        return result(CoverageStatus.REPORTED_BREACH, StatusBasis.EXPLICIT_STATEMENT, documents)

    issuer = dataset.instruments[isin].issuer
    naming = [report.document for report in current if any(e.issuer == issuer for e in report.no_information)]
    if naming:
        return result(CoverageStatus.NO_INFORMATION_REPORTED, StatusBasis.ISSUER_NAMED_AS_NO_INFORMATION, naming)

    trustees = trustees_claimed(dataset, isin)
    if not trustees:
        return result(CoverageStatus.NOT_ASSESSED, StatusBasis.TRUSTEE_UNKNOWN)

    if len(trustees) > 1:
        reviewed_any = any(report.trustee in trustees and report.extraction_complete for report in current)
        if reviewed_any:
            return result(CoverageStatus.AMBIGUOUS, StatusBasis.TRUSTEE_NOT_ESTABLISHED)
        return result(CoverageStatus.NOT_ASSESSED, StatusBasis.TRUSTEE_REPORT_NOT_SEARCHED)

    reviewed: list[BreachReport] = []
    for trustee in sorted(trustees):
        own = [report for report in current if report.trustee == trustee]
        if any(report.extraction_complete for report in own):
            reviewed.extend(report for report in own if report.extraction_complete)
            continue
        if own:
            return result(
                CoverageStatus.NOT_ASSESSED,
                StatusBasis.TRUSTEE_REPORT_INCOMPLETELY_TRANSCRIBED,
                [report.document for report in own],
            )
        searches = [
            search
            for search in dataset.searches.values()
            if search.subject == trustee
            and search.purpose is SearchPurpose.TRUSTEE_REPORT
            and search.period is not None
            and search.period.end == period_end
        ]
        if any(s.outcome in (SearchOutcome.ACCESS_ERROR, SearchOutcome.EXCLUDED_BY_POLICY) for s in searches):
            return result(CoverageStatus.INACCESSIBLE, StatusBasis.TRUSTEE_REPORT_NOT_ACCESSIBLE)
        if any(s.outcome is SearchOutcome.NOT_FOUND for s in searches):
            return result(CoverageStatus.NO_REPORT_FOUND, StatusBasis.TRUSTEE_REPORT_NOT_LOCATED)
        return result(CoverageStatus.NOT_ASSESSED, StatusBasis.TRUSTEE_REPORT_NOT_SEARCHED)
    basis = (
        StatusBasis.TRUSTEE_REPORT_IS_NIL
        if all(report.nil_report for report in reviewed)
        else StatusBasis.NOT_LISTED_IN_TRUSTEE_REPORT
    )
    return result(CoverageStatus.NO_REPORT_FOUND, basis, [report.document for report in reviewed])


def reporting_periods(dataset: Dataset) -> list[date]:
    ends = {report.period.end for report in dataset.breach_reports.values()}
    ends |= {notice.period_end for notice in dataset.breach_notices.values() if notice.period_end}
    ends |= {statement.period.end for statement in dataset.compliance_statements.values()}
    return sorted(ends)


def derive_all(dataset: Dataset) -> list[InstrumentStatus]:
    return [
        derive_status(dataset, isin, period_end)
        for isin in sorted(dataset.instruments)
        for period_end in reporting_periods(dataset)
    ]
