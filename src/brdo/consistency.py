"""Mechanical comparisons between publications that should agree.

Each comparison reports what differs, never why. A trustee's notice and report
may differ for good reason, and a difference is not a finding about conduct.
"""

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from brdo.models import (
    BreachItem,
    BreachNotice,
    BreachReport,
    BreachRow,
    ComplianceStatement,
    Document,
    StatedException,
)
from brdo.pdftext import normalize
from brdo.status import addresses, current_versions, trustees_claimed
from brdo.store import Dataset
from brdo.vocab import (
    ActionKind,
    Agreement,
    CovenantCategory,
    CovenantSpecificity,
    DocumentDateKind,
    NoticeKind,
    StatementMaker,
    StatementScope,
)

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


@dataclass(frozen=True)
class StatementComparison:
    """A compliance statement by an issuer or its auditor, set beside the trustee's report for the same quarter."""

    statement: str
    isin: str
    period_end: date
    made_by: StatementMaker
    scope: StatementScope
    statement_reports_breach: bool
    trustee_report: str | None
    trustee_lists: bool | None
    agreement: Agreement
    basis: str
    levels_only_in_statement: tuple[str, ...]
    statement_dated: date | None
    trustee_received_report: date | None
    trustee_detected: date | None
    trustee_cites_certificate: bool

    @property
    def trustee_could_rely_on_issuer(self) -> bool:
        """Whether the trustee dated its detection on or after the issuer's statement or report reached it."""
        sources = [day for day in (self.statement_dated, self.trustee_received_report) if day is not None]
        return self.trustee_detected is not None and any(self.trustee_detected >= day for day in sources)


_CITES_CERTIFICATE = re.compile(r"certifi|auditor", re.IGNORECASE)

_LEVEL = re.compile(r"(\d+(?:\.\d+)?)\s*(%|x|times|crores?|cr)", re.IGNORECASE)


def _level_key(text: str) -> tuple[float, str] | None:
    match = _LEVEL.search(text)
    if match is None:
        return None
    unit = {"times": "x", "crore": "cr", "crores": "cr"}.get(match.group(2).lower(), match.group(2).lower())
    return float(match.group(1)), unit


def _dated(document: Document) -> date | None:
    return next((day.value for day in document.dates if day.kind is DocumentDateKind.DATED), None)


def _row_text(row: BreachRow) -> str:
    printed = [item.covenant_as_reported for item in row.items]
    printed += [row.security_enforcement_as_reported, row.further_action_as_reported]
    printed += list(row.other_columns_as_reported.values())
    return " ".join(text for text in printed if text)


def _judge(statement: ComplianceStatement, items: list[BreachItem], reviewed: bool) -> tuple[Agreement, str]:
    if not reviewed:
        return Agreement.NOT_COMPARABLE, "no fully transcribed report of the ISIN's trustee for the period"
    if statement.breach_stated:
        if items:
            return Agreement.CONSISTENT, "both report a breach"
        return Agreement.DIFFERS, "the statement reports a breach the trustee's report does not list"
    if not items:
        return Agreement.CONSISTENT, "the statement reports compliance and the trustee's report does not list the ISIN"
    if not addresses(statement, items):
        return Agreement.NOT_COMPARABLE, "the statement covers financial covenants only; the trustee lists another kind"
    return Agreement.DIFFERS, "the statement reports compliance; the trustee's report lists a breach"


def compare_statements_with_reports(dataset: Dataset) -> list[StatementComparison]:
    comparisons = []
    for statement in sorted(dataset.compliance_statements.values(), key=lambda s: s.id):
        period_end = statement.period.end
        reports = [report for report in dataset.breach_reports.values() if report.period.end == period_end]
        current = current_versions(reports, dataset)
        for isin in statement.instruments:
            own = [report for report in current if report.trustee in trustees_claimed(dataset, isin)]
            items = [item for report in own for row in report.rows for item in row.items if isin in item.isins]
            listing = [report.document for report in own if any(isin in row.isins for row in report.rows)]
            complete = [report.document for report in own if report.extraction_complete]
            reviewed = bool(listing) or bool(complete)
            agreement, basis = _judge(statement, items, reviewed)
            reported = {_level_key(level) for item in items for level in item.levels_stated}
            stated = [
                line.required_as_reported
                for line in statement.exceptions
                if isin in line.isins and line.required_as_reported and _level_key(line.required_as_reported)
            ]
            only_stated = (
                tuple(sorted({level for level in stated if _level_key(level) not in reported})) if items else ()
            )
            rows = [row for report in own for row in report.rows if isin in row.isins]
            detected = [row.detected.value for row in rows if row.detected and row.detected.value]
            received = [
                entry.received.value
                for census in dataset.monitoring_censuses.values()
                if census.trustee in {report.trustee for report in own} and census.period.end == period_end
                for entry in census.entries
                if entry.isin == isin and entry.received and entry.received.value
            ]
            comparisons.append(
                StatementComparison(
                    statement=statement.id,
                    isin=isin,
                    period_end=period_end,
                    made_by=statement.made_by,
                    scope=statement.scope,
                    statement_reports_breach=statement.breach_stated,
                    trustee_report=(listing or complete or [None])[0],
                    trustee_lists=bool(items) if reviewed else None,
                    agreement=agreement,
                    basis=basis,
                    levels_only_in_statement=only_stated,
                    statement_dated=_dated(dataset.documents[statement.document]),
                    trustee_received_report=min(received, default=None),
                    trustee_detected=min(detected, default=None),
                    trustee_cites_certificate=any(_CITES_CERTIFICATE.search(_row_text(row)) for row in rows),
                )
            )
    return comparisons


FLOW_FIELDS = ("clause reference", "obligation wording", "required level", "issuer's measured level", "deed dates")
_CLAUSE_REFERENCE = re.compile(
    r"\b(?i:clauses?|schedules?|para(?:graph)?s?|articles?)\s*(?:(?i:no)\.?\s*)?"
    r"(?:\d+(?:\.\d+)*[A-Za-z]?\b(?:\s*\([A-Za-z0-9]{1,4}\))*|[IVXLC]+\b|\([a-z]{1,4}\))"
)
"""A clause, schedule, paragraph or article of the deed named and numbered, such as "Clause no. 10.3 (a)", "Schedule
VIII" or "clause (c)".

A bare number is never a reference: "-1.02%" is a measured level and "30.06.2026" a date, and a numbered heading
such as "2.6 (ii)" counts only where the transcription records it as the row's clause reference. "Section" is left
out because in these disclosures it usually cites a statute. An earlier version read a decimal level as a clause
number.
"""
_OBLIGATION_WORDING = re.compile(r"\b(?:shall|maintain|ensure|not exceed|at least)\b", re.IGNORECASE)


@dataclass(frozen=True)
class FlowEvidence:
    """One exception line, report item or letter that satisfied a field rule, and the exact text that did."""

    document: str
    page: int | None
    locator: str
    matched: str


@dataclass(frozen=True)
class FieldFlow:
    """Whether the issuer's statement and the trustee's publications carry one kind of information about a breach.

    Every line, item or letter that satisfied the rule is kept as evidence, with the text that matched. ``*_examined``
    counts what was looked at, so a "no" after examining nothing can be told from a "no" after examining several.
    """

    statement: str
    isin: str
    field: str
    issuer: bool
    trustee: bool
    issuer_evidence: tuple[FlowEvidence, ...] = ()
    trustee_evidence: tuple[FlowEvidence, ...] = ()
    issuer_examined: int = 0
    trustee_examined: int = 0
    period_end: date | None = None
    trustee_report: str | None = None


def _line_at(document: str, n: int, line: StatedException, matched: str) -> FlowEvidence:
    return FlowEvidence(document, line.page, f"exception line {n}", matched)


def _item_at(report: BreachReport, row: BreachRow, item: BreachItem, matched: str) -> FlowEvidence:
    return FlowEvidence(report.document, item.page, f"row {row.row}", matched)


def field_flows(dataset: Dataset) -> list[FieldFlow]:
    """For each breach both parties report, which of them prints each kind of information, and every line that shows it.

    The rules are mechanical:

    * a clause reference is a named and numbered clause, schedule, paragraph or article (``_CLAUSE_REFERENCE``), and
      on the trustee's side also a clause reference transcribed from the row;
    * wording states the obligation with a verb such as "shall" or "maintain", and on the trustee's side must be in an
      item marked as clause text;
    * a required level is a printed percentage, multiple or amount; on the trustee's side any level printed in the
      cell counts, because ``levels_stated`` does not say which levels are required and which achieved;
    * the issuer's measured level counts for the trustee only if the trustee prints the same number and unit;
    * deed dates on the trustee's side come from its letters for the quarter naming the ISIN.
    """
    flows = []
    for comparison in compare_statements_with_reports(dataset):
        if comparison.agreement is not Agreement.CONSISTENT or not comparison.statement_reports_breach:
            continue
        statement = dataset.compliance_statements[comparison.statement]
        lines = [(n, line) for n, line in enumerate(statement.exceptions, start=1) if comparison.isin in line.isins]
        reports = [r for r in dataset.breach_reports.values() if r.period.end == comparison.period_end]
        own = [r for r in current_versions(reports, dataset) if r.trustee in trustees_claimed(dataset, comparison.isin)]
        items = [(r, row, item) for r in own for row in r.rows for item in row.items if comparison.isin in item.isins]
        notices = sorted(
            (
                n
                for n in dataset.breach_notices.values()
                if comparison.isin in n.isins and n.period_end == comparison.period_end
            ),
            key=lambda n: n.id,
        )

        measured = {}
        for n, line in lines:
            if line.actual_as_reported and (key := _level_key(line.actual_as_reported)) is not None:
                measured.setdefault(key, _line_at(statement.document, n, line, line.actual_as_reported))
        issuer: dict[str, list[FlowEvidence]] = {
            "clause reference": [
                _line_at(statement.document, n, line, match.group(0))
                for n, line in lines
                if (match := _CLAUSE_REFERENCE.search(line.covenant_as_reported))
            ],
            "obligation wording": [
                _line_at(statement.document, n, line, match.group(0))
                for n, line in lines
                if (match := _OBLIGATION_WORDING.search(line.covenant_as_reported))
            ],
            "required level": [
                _line_at(statement.document, n, line, line.required_as_reported)
                for n, line in lines
                if line.required_as_reported and _level_key(line.required_as_reported)
            ],
            "issuer's measured level": list(measured.values()),
            "deed dates": [
                _line_at(statement.document, n, line, line.deed_dates_as_reported)
                for n, line in lines
                if line.deed_dates_as_reported
            ],
        }
        trustee: dict[str, list[FlowEvidence]] = {
            "clause reference": [
                _item_at(r, row, item, item.clause_reference_as_reported or match.group(0))
                for r, row, item in items
                if item.clause_reference_as_reported or (match := _CLAUSE_REFERENCE.search(item.covenant_as_reported))
            ],
            "obligation wording": [
                _item_at(r, row, item, match.group(0))
                for r, row, item in items
                if item.specificity is CovenantSpecificity.CLAUSE_TEXT
                and (match := _OBLIGATION_WORDING.search(item.covenant_as_reported))
            ],
            "required level": [
                _item_at(r, row, item, "; ".join(item.levels_stated)) for r, row, item in items if item.levels_stated
            ],
            "issuer's measured level": [
                _item_at(r, row, item, level)
                for r, row, item in items
                for level in item.levels_stated
                if _level_key(level) in measured
            ],
            "deed dates": [
                FlowEvidence(n.document, n.page, f"letter {n.id}", ", ".join(str(day) for day in n.deed_dates))
                for n in notices
                if n.deed_dates
            ],
        }
        for field in FLOW_FIELDS:
            trustee_examined = len(notices) if field == "deed dates" else len(items)
            flows.append(
                FieldFlow(
                    comparison.statement,
                    comparison.isin,
                    field,
                    bool(issuer[field]),
                    bool(trustee[field]),
                    tuple(issuer[field]),
                    tuple(trustee[field]),
                    len(lines),
                    trustee_examined,
                    comparison.period_end,
                    comparison.trustee_report,
                )
            )
    return flows


ENFORCEMENT = "enforcement step or nominee director reported"
WAIVER = "waiver reported"
NO_ACTION = "holders instructed no action"
CURE_FINANCIAL = "cure reported for a financial covenant"
CURE_OTHER = "cure reported for another obligation, such as a late filing"
CURE_UNATTRIBUTED = "cure reported, for covenants of more than one kind"
HELD = "meeting reported as held"
ADJOURNED = "meeting adjourned for lack of quorum"
SCHEDULED = "meeting reported as scheduled"
PENDING = "awaiting instructions, following up or continuing"

FOLLOW_UP_STATES = (
    (ENFORCEMENT, frozenset({ActionKind.ENFORCEMENT, ActionKind.NOMINEE_DIRECTOR})),
    (WAIVER, frozenset({ActionKind.WAIVER_REPORTED})),
    (NO_ACTION, frozenset({ActionKind.NO_ACTION_INSTRUCTED})),
    (CURE_FINANCIAL, frozenset()),
    (CURE_OTHER, frozenset()),
    (CURE_UNATTRIBUTED, frozenset()),
    (HELD, frozenset({ActionKind.HOLDERS_MEETING_HELD})),
    (ADJOURNED, frozenset()),
    (SCHEDULED, frozenset({ActionKind.HOLDERS_MEETING_SCHEDULED})),
    (
        PENDING,
        frozenset(
            {
                ActionKind.AWAITING_INSTRUCTIONS,
                ActionKind.FOLLOW_UP_WITH_ISSUER,
                ActionKind.REPORTED_AS_CONTINUING,
                ActionKind.OTHER,
            }
        ),
    ),
)
"""Published follow-up states, in the report's order. The first six are outcomes; none is ranked above another."""
OUTCOME_STATES = frozenset({ENFORCEMENT, WAIVER, NO_ACTION, CURE_FINANCIAL, CURE_OTHER, CURE_UNATTRIBUTED})


class PeriodAttribution(StrEnum):
    """How a follow-up state is tied to a reporting period."""

    REPORT_ROW = "report_row"
    """From a row of the trustee's report for the period."""
    LETTER_PERIOD = "letter_period"
    """From a letter whose quarter the project recorded as stated or evident in it."""
    LINKED_BY_RULE = "linked_by_rule"
    """From a letter naming no quarter that continues, by a stated rule, a letter of the same file that does."""
    NOT_ATTRIBUTABLE = "not_attributable"
    """From a letter naming no quarter that the rule cannot link to one. Counted for no period."""


@dataclass(frozen=True)
class FollowUpState:
    """One follow-up state a trustee publishes for an ISIN, with where the record shows it and how its period is known.

    ``period_end`` is empty when the state comes from a letter that cannot be tied to a period.
    """

    trustee: str
    isin: str
    period_end: date | None
    state: str
    basis: str
    attribution: PeriodAttribution = PeriodAttribution.REPORT_ROW


@dataclass(frozen=True)
class ContinuationLink:
    """Which quarter a letter continuing an adjourned meeting belongs to, for one ISIN, if a rule can tell."""

    letter: str
    isin: str
    period_end: date | None
    continues: tuple[str, ...]
    reason: str


def link_continuations(dataset: Dataset) -> dict[tuple[str, str], ContinuationLink]:
    """Tie each continuation letter, ISIN by ISIN, to the quarter of the meeting it continues, where a rule allows.

    The rule: the same file holds a breach letter of the same trustee naming the same ISIN, with a recorded quarter
    and a meeting proposed on or before the continuation's date, and every such letter names one quarter. The rule
    reads the file's order, not the letter's words: the continuation itself states no quarter. Where no such letter
    exists, or they name different quarters, the continuation is tied to no period.
    """
    breach_letters = [n for n in dataset.breach_notices.values() if n.kind is NoticeKind.BREACH]
    links: dict[tuple[str, str], ContinuationLink] = {}
    for letter in dataset.breach_notices.values():
        if letter.kind is not NoticeKind.MEETING_CONTINUATION or letter.period_end is not None:
            continue
        for isin in letter.isins:
            earlier = [
                n
                for n in breach_letters
                if n.document == letter.document
                and n.trustee == letter.trustee
                and isin in n.isins
                and n.period_end is not None
                and n.meeting_proposed_for is not None
                and n.meeting_proposed_for <= letter.issued_on
            ]
            periods = sorted({n.period_end for n in earlier})
            continues = tuple(sorted(n.id for n in earlier))
            if len(periods) == 1:
                reason = f"continues {', '.join(continues)} of the same file, whose meeting came first"
                links[(letter.id, isin)] = ContinuationLink(letter.id, isin, periods[0], continues, reason)
            elif periods:
                reason = f"earlier letters of the same file name different quarters: {', '.join(continues)}"
                links[(letter.id, isin)] = ContinuationLink(letter.id, isin, None, continues, reason)
            else:
                reason = "no earlier letter of the same file names this ISIN with a quarter and an earlier meeting"
                links[(letter.id, isin)] = ContinuationLink(letter.id, isin, None, (), reason)
    return links


def _cure_state(categories: set[CovenantCategory]) -> str:
    """A cure is typed only when every covenant it can concern is of one kind; a mixed row's cure is not typed."""
    if categories == {CovenantCategory.FINANCIAL}:
        return CURE_FINANCIAL
    if CovenantCategory.FINANCIAL not in categories:
        return CURE_OTHER
    return CURE_UNATTRIBUTED


def _letter_states(notice: BreachNotice, isin: str, period_end: date | None, attribution, suffix: str = ""):
    if notice.adjourned_for_lack_of_quorum:
        yield FollowUpState(notice.trustee, isin, period_end, ADJOURNED, f"letter {notice.id}{suffix}", attribution)
    if notice.meeting_proposed_for:
        basis = f"letter {notice.id}: meeting proposed for {notice.meeting_proposed_for}{suffix}"
        yield FollowUpState(notice.trustee, isin, period_end, SCHEDULED, basis, attribution)


def follow_up_states(dataset: Dataset, period_end: date) -> tuple[list[FollowUpState], list[tuple[str, str]]]:
    """Every follow-up state published for the ISINs listed in the current reports for a period, and those ISINs.

    States come from the project's reading of each report's action cells, and from the trustee's letters naming the
    ISIN. A cure is typed by the covenant categories of the row's items for that ISIN, and only when they are all of
    one kind, so a late filing made good is never a financial covenant restored. A letter naming another quarter is not
    counted. A letter naming none is counted only when ``link_continuations`` ties it to this quarter.
    """
    reports = current_versions([r for r in dataset.breach_reports.values() if r.period.end == period_end], dataset)
    listed: set[tuple[str, str]] = set()
    found: set[FollowUpState] = set()
    for report in reports:
        for row in report.rows:
            kinds = {action.kind for action in row.actions}
            where = f"{report.document} row {row.row}"
            for isin in row.isins:
                listed.add((report.trustee, isin))
                for state, wanted in FOLLOW_UP_STATES:
                    if hit := sorted(kind.value for kind in kinds & wanted):
                        found.add(FollowUpState(report.trustee, isin, period_end, state, f"{where}: {', '.join(hit)}"))
                if ActionKind.CURE_REPORTED in kinds:
                    categories = {item.category for item in row.items if isin in item.isins}
                    basis = (
                        f"{where}: cure_reported, covenant categories {', '.join(sorted(c.value for c in categories))}"
                    )
                    found.add(FollowUpState(report.trustee, isin, period_end, _cure_state(categories), basis))
    links = link_continuations(dataset)
    for notice in dataset.breach_notices.values():
        for isin in notice.isins:
            if (notice.trustee, isin) not in listed:
                continue
            if notice.period_end is not None:
                if notice.period_end == period_end:
                    found.update(_letter_states(notice, isin, period_end, PeriodAttribution.LETTER_PERIOD))
                continue
            link = links.get((notice.id, isin))
            if link is not None and link.period_end == period_end:
                suffix = f"; {link.reason} (linked by rule)"
                found.update(_letter_states(notice, isin, period_end, PeriodAttribution.LINKED_BY_RULE, suffix))
    order = {state: index for index, (state, _) in enumerate(FOLLOW_UP_STATES)}
    states = sorted(found, key=lambda s: (s.trustee, s.isin, order[s.state], s.basis))
    return states, sorted(listed)


def unattributed_follow_up(dataset: Dataset) -> list[FollowUpState]:
    """Follow-up states from letters that name no quarter and cannot be tied to one. They count for no period."""
    found = []
    for (letter_id, isin), link in link_continuations(dataset).items():
        if link.period_end is not None:
            continue
        notice = dataset.breach_notices[letter_id]
        found += _letter_states(notice, isin, None, PeriodAttribution.NOT_ATTRIBUTABLE, f"; {link.reason}")
    return sorted(found, key=lambda s: (s.trustee, s.isin, s.state, s.basis))
