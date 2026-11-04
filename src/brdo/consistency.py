"""Mechanical comparisons between publications that should agree.

Each comparison reports what differs, never why. A trustee's notice and report
may differ for good reason, and a difference is not a finding about conduct.
"""

import re
from dataclasses import dataclass
from datetime import date

from brdo.models import BreachNotice, BreachReport, BreachRow
from brdo.pdftext import normalize
from brdo.status import current_versions
from brdo.store import Dataset
from brdo.vocab import NoticeKind

_THRESHOLD = re.compile(r"\d+(?:[.,]\d+)*\s*(?:%|x\b|times\b|crores?\b|cr\b)", re.IGNORECASE)


def stated_thresholds(text: str) -> frozenset[str]:
    """Percentages, multiples and crore amounts printed in a covenant's text."""
    return frozenset(re.sub(r"\s+", "", match.group(0)).lower() for match in _THRESHOLD.finditer(normalize(text)))


@dataclass(frozen=True)
class NoticeComparison:
    notice: str
    isin: str
    report: str
    row: str
    issuer_intimation: date | None
    detected: date | None
    thresholds_in_notice: frozenset[str] | None
    thresholds_in_report: frozenset[str]

    @property
    def days_from_intimation_to_detection(self) -> int | None:
        if self.issuer_intimation is None or self.detected is None:
            return None
        return (self.detected - self.issuer_intimation).days

    @property
    def thresholds_agree(self) -> bool | None:
        """None when the notice states no level, or quotes too little of the cell to compare."""
        if not self.thresholds_in_notice:
            return None
        return self.thresholds_in_notice == self.thresholds_in_report


def _closest_row(rows: list[BreachRow], notice: BreachNotice) -> BreachRow:
    anchor = notice.issuer_intimation or notice.issued_on

    def distance(row: BreachRow) -> int:
        detected = row.detected.value if row.detected else None
        return abs((detected - anchor).days) if detected else 10**6

    return min(rows, key=distance)


def _report_for(dataset: Dataset, notice: BreachNotice, isin: str) -> BreachReport | None:
    reports = [
        report
        for report in dataset.breach_reports.values()
        if report.trustee == notice.trustee and report.period.end == notice.period_end
    ]
    for report in current_versions(reports, dataset):
        if any(isin in row.isins for row in report.rows):
            return report
    return None


def compare_notices_with_reports(dataset: Dataset) -> list[NoticeComparison]:
    comparisons = []
    for notice in sorted(dataset.breach_notices.values(), key=lambda n: n.id):
        if notice.kind is not NoticeKind.BREACH or not notice.isins_printed:
            continue
        for isin in notice.isins:
            report = _report_for(dataset, notice, isin)
            if report is None:
                continue
            row = _closest_row([row for row in report.rows if isin in row.isins], notice)
            reported = {level for item in row.items if isin in item.isins for level in item.levels_stated}
            comparisons.append(
                NoticeComparison(
                    notice=notice.id,
                    isin=isin,
                    report=report.document,
                    row=row.row,
                    issuer_intimation=notice.issuer_intimation,
                    detected=row.detected.value if row.detected else None,
                    thresholds_in_notice=frozenset(notice.levels_stated) if notice.levels_complete else None,
                    thresholds_in_report=frozenset(reported),
                )
            )
    return comparisons


@dataclass(frozen=True)
class Revision:
    earlier: str
    later: str
    isin: str
    field: str
    before: str
    after: str


def revisions(dataset: Dataset) -> list[Revision]:
    """What changed for each ISIN between a report and the later version that supersedes it."""
    found = []
    for report in sorted(dataset.breach_reports.values(), key=lambda r: r.document):
        for earlier_id in dataset.documents[report.document].supersedes:
            earlier = dataset.breach_reports.get(earlier_id)
            if earlier is None:
                continue
            before = {isin: row for row in earlier.rows for isin in row.isins}
            after = {isin: row for row in report.rows for isin in row.isins}
            for isin in sorted(before.keys() | after.keys()):
                old, new = before.get(isin), after.get(isin)
                if old is None or new is None:
                    found.append(
                        Revision(
                            earlier_id,
                            report.document,
                            isin,
                            "listed",
                            "listed" if old else "not listed",
                            "listed" if new else "not listed",
                        )
                    )
                elif old.further_action_as_reported != new.further_action_as_reported:
                    found.append(
                        Revision(
                            earlier_id,
                            report.document,
                            isin,
                            "further_action",
                            old.further_action_as_reported or "",
                            new.further_action_as_reported or "",
                        )
                    )
    return found
