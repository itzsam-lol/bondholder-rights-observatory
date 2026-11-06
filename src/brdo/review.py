"""Materials for a label-blind second annotation, and the rules that keep a review honest.

A packet lists each judgement to be made again: the document and page it rests on, a locator, a passage where the
record transcribes the very cell being judged, the allowed values and the rule of ``docs/annotation-codebook.md`` that
applies. It never gives the current value or the record's id. It is label-blind, not blind: the current values are in
the project's public exports, and a reviewer who searched them by ISIN or document could find them, so the review also
relies on the reviewer's undertaking not to look. Hard cases are flagged from the source text alone, with a note that
says what makes them hard and not what to choose. The key, which holds the current values, is written to a separate
directory.

``score`` compares a second annotator's answers with the key, field by field and never pooled, with raw agreement,
kappa where it is stable enough to report, the counts behind every statistic and every disagreement.
``submission_errors`` lists the faults that stop an answers file being scored at all.

Nothing here marks an annotation as reviewed. A review is an ``AnnotationReview`` in ``data/annotation-reviews.yaml``,
made by a person other than the original annotator, keeping the original, second and adjudicated values and the
reasons for them. Re-applying the same rules, the same curator re-reading, or another pass by an automated process is
not a review and must not be recorded as one. ``review_problems`` enforces what the records can show of this.
"""

from __future__ import annotations

import csv
import dataclasses
import io
import re
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from brdo.models import AnnotationReview, BreachItem, Provision
from brdo.vocab import (
    ActionKind,
    Agreement,
    CovenantCategory,
    CovenantSpecificity,
    NoticeKind,
    ProvisionStage,
    StatementMaker,
    StatementScope,
)

if TYPE_CHECKING:
    from brdo.store import Dataset

CODEBOOK = Path("docs") / "annotation-codebook.md"
GUIDE = Path("docs") / "reviewer-guide.md"
BOOLEAN = ("true", "false")
DATE_OR_NONE = "a date as YYYY-MM-DD, or none"
NONE = "none"

PACKET_COLUMNS = [
    "decision",
    "field",
    "kind",
    "allowed",
    "multiple",
    "document",
    "url",
    "sha256",
    "page",
    "locator",
    "isins",
    "passage",
    "hard_case",
    "hard_case_note",
    "rule",
]
ANSWER_COLUMNS = ["decision", "field", "value", "unsure", "reason", "problem"]
PROBLEMS = ("source_unavailable", "hash_mismatch", "page_not_found", "cannot_interpret")
"""What a reviewer reports when a source cannot be used; see ``docs/reviewer-guide.md``."""
KEY_COLUMNS = ["decision", "decision_id", "record", "field", "value", "hard_case"]


def canonical(value: object) -> str:
    """A value as packets, keys and answers write it."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, list | tuple | set | frozenset):
        return "|".join(sorted({canonical(item) for item in value}))
    return str(value)


def normalise_answer(text: str, multiple: bool) -> str:
    """An answer as written by a person, read the way the key is written."""
    if multiple:
        labels = sorted({part.strip().lower() for part in text.split("|") if part.strip()})
        return "|".join(label for label in labels if label != NONE) or (NONE if NONE in labels else "")
    stripped = text.strip()
    return stripped.lower() if stripped.lower() in (*BOOLEAN, NONE) else stripped


@dataclass(frozen=True)
class Decision:
    """One judgement a second annotator makes again. ``value`` is never written to a packet."""

    id: str
    field: str
    record: str
    allowed: str
    multiple: bool
    value: str
    document: str
    url: str
    page: int | None
    locator: str
    passage: str
    rule: str
    hard_case_note: str | None = None
    isins: tuple[str, ...] = ()
    sha256: str = ""

    @property
    def kind(self) -> str:
        """How the decision's values are compared: ``categorical``, ``binary``, ``multi_label`` or ``date``."""
        return FIELD_KINDS[self.field]

    def packet_row(self, packet_id: str) -> dict[str, object]:
        """The line a packet gives the annotator: no value, and an id for this round instead of the record's own."""
        return {
            "decision": packet_id,
            "field": self.field,
            "kind": self.kind,
            "allowed": self.allowed,
            "multiple": "true" if self.multiple else "false",
            "document": self.document,
            "url": self.url,
            "sha256": self.sha256,
            "page": "" if self.page is None else self.page,
            "locator": self.locator,
            "isins": "|".join(self.isins),
            "passage": self.passage,
            "hard_case": "true" if self.hard_case_note else "false",
            "hard_case_note": self.hard_case_note or "",
            "rule": self.rule,
        }


def _choices(values: Iterable[Enum]) -> str:
    return "|".join(str(value.value) for value in values)


@dataclass(frozen=True)
class HardCase:
    """A kind of passage on which careful readers could reasonably differ, recognised from the text alone."""

    fields: frozenset[str]
    applies: Callable[[str, BreachItem | Provision], bool]
    note: str


def _matches(pattern: str) -> Callable[[str, BreachItem | Provision], bool]:
    compiled = re.compile(pattern, re.IGNORECASE)
    return lambda text, record: bool(compiled.search(text))


def _ratio_without_level(text: str, record: BreachItem | Provision) -> bool:
    return isinstance(record, BreachItem) and not record.levels_stated and bool(re.search(r"\bratio\b", text, re.I))


HARD_CASES = (
    HardCase(
        frozenset({"breach_item.category", "provision.category"}),
        _matches(r"security\s+cover"),
        "Concerns security cover. Apply the general rules, and give a reason.",
    ),
    HardCase(
        frozenset({"breach_item.category", "provision.category"}),
        _matches(r"governance"),
        "Concerns corporate governance requirements. Apply the general rules, and give a reason.",
    ),
    HardCase(
        frozenset({"breach_item.category"}),
        _matches(r"\blist(?:ed|ing)\b"),
        "Concerns listing. Apply the general rules, and give a reason.",
    ),
    HardCase(
        frozenset({"breach_item.category"}),
        _matches(r"\b(?:negative|affirmative|financial|information)\s+covenants?\b"),
        "Names a class of covenants but not the undertaking itself. Apply the general rules, and give a reason.",
    ),
    HardCase(
        frozenset({"breach_item.category", "provision.category"}),
        _matches(r"\b(?:non[\s-]*payment|payment of (?:interest|principal))\b"),
        "Concerns payment of interest or principal. Apply the general rules, and give a reason.",
    ),
    HardCase(
        frozenset({"breach_item.specificity"}),
        _ratio_without_level,
        "Names or defines a ratio, and no percentage, multiple or crore amount was found in the cell. Apply the "
        "general rules, and give a reason.",
    ),
)


def _hard_case(field_name: str, text: str, record: BreachItem | Provision) -> str | None:
    notes = [case.note for case in HARD_CASES if field_name in case.fields and case.applies(text, record)]
    return " ".join(notes) or None


def _row_labels(rows: list) -> list[str]:
    """Printed row numbers, with a part number where one printed row is split into several records."""
    counts = Counter(row.row for row in rows)
    seen: Counter[str] = Counter()
    labels = []
    for row in rows:
        seen[row.row] += 1
        labels.append(row.row if counts[row.row] == 1 else f"{row.row}.{seen[row.row]}")
    return labels


def decisions(dataset: Dataset) -> list[Decision]:
    """Every annotated judgement in the dataset, as a decision a second annotator can make again."""
    out: list[Decision] = []

    def url(document_id: str) -> str:
        document = dataset.documents.get(document_id)
        return "" if document is None else document.url

    for report in sorted(dataset.breach_reports.values(), key=lambda r: r.document):
        for row, label in zip(report.rows, _row_labels(report.rows), strict=True):
            row_id = f"{report.document}:row-{label}"
            printed = f"row {row.row}" if label == row.row else f"row {row.row} (part {label.split('.')[1]})"
            action_cells = [
                ("Security enforcement", row.security_enforcement_as_reported),
                ("Further action", row.further_action_as_reported),
                *row.other_columns_as_reported.items(),
            ]
            out.append(
                Decision(
                    id=f"{row_id}:actions",
                    field="breach_row.actions",
                    record=row_id,
                    allowed=_choices(ActionKind) + f"|{NONE}",
                    multiple=True,
                    value=canonical([action.kind for action in row.actions]) or NONE,
                    document=report.document,
                    url=url(report.document),
                    page=row.page,
                    locator=f"{printed}, action columns",
                    passage=" / ".join(f"{name}: {text}" for name, text in action_cells if text),
                    rule="annotation-codebook.md#actions",
                    isins=tuple(row.isins),
                )
            )
            out.append(
                Decision(
                    id=f"{row_id}:carried_over_from",
                    field="breach_row.carried_over_from",
                    record=row_id,
                    allowed=DATE_OR_NONE,
                    multiple=False,
                    value=canonical(row.carried_over_from) or NONE,
                    document=report.document,
                    url=url(report.document),
                    page=row.page,
                    locator=f"{printed}, its label",
                    passage="",
                    rule="annotation-codebook.md#carried-over-breaches",
                    isins=tuple(row.isins),
                )
            )
            for index, item in enumerate(row.items, start=1):
                item_id = f"{row_id}:item-{index}"
                passage = item.covenant_as_reported + (" [the cell continues in the source]" if item.truncated else "")
                where = f"{printed}, covenant cell {index}"
                for name, allowed, value, rule in (
                    ("category", _choices(CovenantCategory), item.category, "covenant-category"),
                    ("specificity", _choices(CovenantSpecificity), item.specificity, "specificity"),
                    ("assignment_uncertain", "|".join(BOOLEAN), item.assignment_uncertain, "row-assignment"),
                ):
                    field_name = f"breach_item.{name}"
                    out.append(
                        Decision(
                            id=f"{item_id}:{name}",
                            field=field_name,
                            record=item_id,
                            allowed=allowed,
                            multiple=False,
                            value=canonical(value),
                            document=report.document,
                            url=url(report.document),
                            page=item.page,
                            locator=where,
                            passage=passage,
                            rule=f"annotation-codebook.md#{rule}",
                            isins=tuple(item.isins),
                            hard_case_note=_hard_case(field_name, item.covenant_as_reported, item),
                        )
                    )
                for link in item.provisions:
                    clause = dataset.provisions.get(link.provision)
                    clause_text = "" if clause is None else f" / Clause record ({clause.clause}): {clause.text}"
                    out.append(
                        Decision(
                            id=f"{item_id}:link-{link.provision}:agreement",
                            field="provision_link.agreement",
                            record=f"{item_id}:link-{link.provision}",
                            allowed=_choices(Agreement),
                            multiple=False,
                            value=canonical(link.agreement),
                            document=report.document,
                            url=url(report.document),
                            page=item.page,
                            locator=f"{where}, against clause record {link.provision}",
                            passage=f"Trustee's cell: {passage}{clause_text}",
                            rule="annotation-codebook.md#links-between-cells-and-clauses",
                            isins=tuple(item.isins),
                        )
                    )

    for notice in sorted(dataset.breach_notices.values(), key=lambda n: n.id):
        # Only some letters have a transcribed covenant or deed, and which ones depends on the values under review,
        # so no letter decision carries a passage: the page, the letter's date and its ISINs locate it.
        for name, allowed, value in (
            ("kind", _choices(NoticeKind), notice.kind),
            ("period_end", DATE_OR_NONE, notice.period_end),
            ("adjourned_for_lack_of_quorum", "|".join(BOOLEAN), notice.adjourned_for_lack_of_quorum),
        ):
            out.append(
                Decision(
                    id=f"{notice.id}:{name}",
                    field=f"notice.{name}",
                    record=notice.id,
                    allowed=allowed,
                    multiple=False,
                    value=canonical(value) or NONE,
                    document=notice.document,
                    url=url(notice.document),
                    page=notice.page,
                    locator=f"letter dated {notice.issued_on.isoformat()}",
                    passage="",
                    rule="annotation-codebook.md#letters",
                    isins=tuple(notice.isins),
                )
            )

    for statement in sorted(dataset.compliance_statements.values(), key=lambda s: s.id):
        # The record's own quotations were chosen as evidence for its values, so they are not given: the reviewer
        # gets the pages and the ISINs, and reads the statement and any annexure there.
        pages = sorted({item.page for item in statement.evidence if item.page is not None})
        page = pages[0] if pages else None
        where = (
            f"statement for {statement.period.start.isoformat()} to {statement.period.end.isoformat()}, "
            f"as it applies to the ISINs in isins; the record cites page{'s' if len(pages) > 1 else ''} "
            + ", ".join(str(number) for number in pages)
        )
        for name, allowed, value in (
            ("made_by", _choices(StatementMaker), statement.made_by),
            ("scope", _choices(StatementScope), statement.scope),
            ("breach_stated", "|".join(BOOLEAN), statement.breach_stated),
            ("isins_printed", "|".join(BOOLEAN), statement.isins_printed),
        ):
            out.append(
                Decision(
                    id=f"{statement.id}:{name}",
                    field=f"statement.{name}",
                    record=statement.id,
                    allowed=allowed,
                    multiple=False,
                    value=canonical(value),
                    document=statement.document,
                    url=url(statement.document),
                    page=page,
                    locator=where,
                    passage="",
                    rule="annotation-codebook.md#compliance-statements",
                    isins=tuple(statement.instruments),
                )
            )

    for provision in sorted(dataset.provisions.values(), key=lambda p: p.id):
        for name, allowed, value in (
            ("category", _choices(CovenantCategory), provision.category),
            ("stage", _choices(ProvisionStage), provision.stage),
        ):
            field_name = f"provision.{name}"
            out.append(
                Decision(
                    id=f"{provision.id}:{name}",
                    field=field_name,
                    record=provision.id,
                    allowed=allowed,
                    multiple=False,
                    value=canonical(value),
                    document=provision.document,
                    url=url(provision.document),
                    page=provision.page,
                    locator=f"clause {provision.clause}",
                    passage=provision.text,
                    rule="annotation-codebook.md#clause-records",
                    isins=tuple(provision.instruments),
                    hard_case_note=_hard_case(field_name, provision.text, provision),
                )
            )
    return [
        dataclasses.replace(d, sha256=getattr(dataset.documents.get(d.document), "sha256", None) or "") for d in out
    ]


FIELD_KINDS = {
    "breach_item.category": "categorical",
    "breach_item.specificity": "categorical",
    "breach_item.assignment_uncertain": "binary",
    "breach_row.actions": "multi_label",
    "breach_row.carried_over_from": "date",
    "provision_link.agreement": "categorical",
    "notice.kind": "categorical",
    "notice.period_end": "date",
    "notice.adjourned_for_lack_of_quorum": "binary",
    "statement.made_by": "categorical",
    "statement.scope": "categorical",
    "statement.breach_stated": "binary",
    "statement.isins_printed": "binary",
    "provision.category": "categorical",
    "provision.stage": "categorical",
}


def _write_csv(path: Path, columns: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file, ignoring a byte-order mark such as a spreadsheet may add when saving."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


INSTRUCTIONS = """Second annotation packet

Read guide.md first, then codebook.md and the SEBI annex it names. For each line of decisions.csv, download the
document from its address, check that its SHA-256 matches, go to the page and the locator, and read the source there,
with the passage where there is one. Then fill in the matching line of answers.csv:

- value: one of the allowed values (several separated by | where multiple is true). none is a value: write it where the
  allowed values offer it and there is nothing to record. A blank value with no problem code means you could not
  decide, and is counted as unanswered; a blank value with a problem code is recorded as excluded for that reason.
- unsure: true or false.
- reason: required for every hard case, every answer marked unsure, every blank value and every problem.
- problem: empty, or exactly one of {problems}. A value given with source_unavailable, hash_mismatch or
  page_not_found is not scored; with cannot_interpret, set unsure to true.

Do not look at the project's data, exports, reports or repository until you have returned your answers, and do not use
an AI tool or other automated aid to decide. Return only answers.csv. The answer key is not in this folder.

Codebook commit: {commit}
Round: {round}
Decisions: {count}, in {documents} documents; {hard} are hard cases

Fields in this packet:

{fields}
"""

ROUNDS = ("1", "2", "all")
"""Round 1: the decisions behind the main comparisons and closure findings. Round 2: everything else."""


def round_fields(dataset: Dataset, chosen: str) -> Callable[[Decision], bool]:
    """Which decisions a review round includes, chosen by field and record, never by the current value.

    Round 1 holds every decision about compliance statements, every row's actions, every letter's kind, quarter and
    adjournment, every covenant cell's category, and the specificity of the cells listing an ISIN that a statement
    covers. Those carry the statement comparisons, what each party adds, and the follow-up and cure findings. Round 2
    holds the rest: other cells' specificity, row assignment, carried-over quarters, clause records and links.
    """
    compared = {isin for statement in dataset.compliance_statements.values() for isin in statement.instruments}
    first = {"breach_row.actions", "notice.kind", "notice.period_end", "notice.adjourned_for_lack_of_quorum"}

    def in_round_one(decision: Decision) -> bool:
        if decision.field.startswith("statement.") or decision.field in first:
            return True
        if decision.field == "breach_item.category":
            return True
        return decision.field == "breach_item.specificity" and bool(set(decision.isins) & compared)

    if chosen == "1":
        return in_round_one
    if chosen == "2":
        return lambda decision: not in_round_one(decision)
    return lambda decision: True


class PacketRefused(Exception):
    """A packet would be written somewhere its key could be published or mixed with another round's."""


def write_packet(
    dataset: Dataset,
    directory: Path,
    codebook: Path,
    commit: str,
    fields: set[str] | None = None,
    chosen_round: str = "all",
    repository: Path | None = None,
    guide: Path | None = None,
) -> dict:
    """Write the packet for the annotator and, apart from it, the key.

    Packet lines carry ids for this round only (``D0001``...), because record ids are the curator's and could hint
    at a value. The key maps them to the stable decision ids that review records use. The output directory must lie
    outside ``repository``, so that the key cannot be committed or published with the exports, and must not already
    hold a packet or key. The key is readable by its owner only.
    """
    target = directory.resolve()
    if repository is not None and target.is_relative_to(repository.resolve()):
        raise PacketRefused(f"{directory} is inside the repository; write the packet and its key outside it")
    packet, key = directory / "packet", directory / "key"
    if packet.exists() or key.exists():
        raise PacketRefused(f"{directory} already holds a packet or a key; use a new directory for each round")
    included = round_fields(dataset, chosen_round)
    chosen = [d for d in decisions(dataset) if (fields is None or d.field in fields) and included(d)]
    ids = [f"D{number:04d}" for number in range(1, len(chosen) + 1)]
    _write_csv(packet / "decisions.csv", PACKET_COLUMNS, (d.packet_row(i) for i, d in zip(ids, chosen, strict=True)))
    _write_csv(
        packet / "answers.csv",
        ANSWER_COLUMNS,
        (
            {"decision": i, "field": d.field, "value": "", "unsure": "", "reason": "", "problem": ""}
            for i, d in zip(ids, chosen, strict=True)
        ),
    )
    (packet / "codebook.md").write_text(codebook.read_text(encoding="utf-8"), encoding="utf-8")
    if guide is not None:
        (packet / "guide.md").write_text(guide.read_text(encoding="utf-8"), encoding="utf-8")
    counts = Counter(d.field for d in chosen)
    allowed = {d.field: (d.kind, d.allowed) for d in chosen}
    field_table = "\n".join(
        f"  {name}: {count} decisions, {allowed[name][0]}; allowed: {allowed[name][1]}"
        for name, count in sorted(counts.items())
    )
    (packet / "README.txt").write_text(
        INSTRUCTIONS.format(
            commit=commit,
            round=chosen_round,
            count=len(chosen),
            documents=len({d.document for d in chosen}),
            hard=sum(1 for d in chosen if d.hard_case_note),
            problems=", ".join(PROBLEMS),
            fields=field_table,
        ),
        encoding="utf-8",
    )
    key.mkdir(parents=True, mode=0o700)
    key.chmod(0o700)
    _write_csv(
        key / "key.csv",
        KEY_COLUMNS,
        (
            {
                "decision": i,
                "decision_id": d.id,
                "record": d.record,
                "field": d.field,
                "value": d.value,
                "hard_case": "true" if d.hard_case_note else "false",
            }
            for i, d in zip(ids, chosen, strict=True)
        ),
    )
    (key / "key.csv").chmod(0o600)
    return {"packet": packet, "key": key, "decisions": len(chosen)}


def cohen_kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa for two annotators' values. None when it is undefined, because chance agreement is certain."""
    if not pairs:
        return None
    observed = sum(1 for first, second in pairs if first == second) / len(pairs)
    firsts, seconds = Counter(first for first, _ in pairs), Counter(second for _, second in pairs)
    expected = sum(firsts[value] * seconds[value] for value in firsts) / len(pairs) ** 2
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def specific_agreement(pairs: list[tuple[str, str]], positive: str) -> float | None:
    """Agreement on one value of a binary or per-label decision: 2a / (2a + b + c), where a is joint use of the value
    and b and c are the two kinds of disagreement about it. Undefined when neither annotator ever uses it."""
    both = sum(1 for first, second in pairs if first == second == positive)
    one = sum(1 for first, second in pairs if (first == positive) != (second == positive))
    return None if both == 0 and one == 0 else 2 * both / (2 * both + one)


def _labels(value: str) -> set[str]:
    return set() if value in ("", NONE) else set(value.split("|"))


def _jaccard(first: str, second: str) -> float:
    a, b = _labels(first), _labels(second)
    return 1.0 if not a and not b else len(a & b) / len(a | b)


EXCLUDING = ("source_unavailable", "hash_mismatch", "page_not_found")
"""Problem codes meaning the cited page of the recorded file was not read: the decision is excluded, value or not."""
INTERPRET = "cannot_interpret"
"""The one problem code that may come with a value: the reviewer's best reading, which the guide asks to mark unsure."""
KAPPA_MIN_PAIRS = 20
KAPPA_MAX_SHARE = 0.9
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def answer_error(raw: str, kind: str, allowed: str, multiple: bool) -> str | None:
    """Why an answer's value cannot be scored, or None. A value is never guessed into an allowed one."""
    text = raw.strip()
    if kind == "date":
        if text.lower() == NONE:
            return None
        if not _ISO_DATE.fullmatch(text):
            return "not a date written as YYYY-MM-DD, or none"
        try:
            date.fromisoformat(text)
        except ValueError:
            return "not a real date"
        return None
    choices = {value.lower() for value in allowed.split("|") if value} if allowed else set()
    if not choices and kind == "binary":
        choices = set(BOOLEAN)
    labels = [part.strip().lower() for part in text.split("|")] if multiple else [text.lower()]
    if multiple and NONE in labels and len(set(labels)) > 1:
        return "none together with other values"
    if any(not label for label in labels):
        return "an empty value between separators"
    if choices:
        unknown = sorted({label for label in labels if label not in choices})
        if unknown:
            return f"not among the allowed values: {', '.join(unknown)}"
    if not multiple and "|" in text:
        return "several values where one is allowed"
    return None


@dataclass
class FieldScore:
    """Agreement on one field. Fields are never pooled.

    Every decision falls in exactly one of four categories:

    - ``missing``: the answers have no line for it;
    - ``blank``: a line with no value and no problem code, which is unfinished, not a negative answer;
    - excluded, either by a recognised problem code (``excluded``: ``source_unavailable``, ``hash_mismatch`` or
      ``page_not_found``, with or without a value, or ``cannot_interpret`` without a value), or because the response
      cannot be read as an answer (``invalid``: a value that is not allowed, an unrecognised or combined problem
      code, a line naming another field, or a decision answered more than once);
    - ``answered``: a valid value, which alone enters agreement.

    ``warnings`` lists answered or blank lines with a fault that does not change the category, such as a value given
    with ``cannot_interpret`` but not marked unsure.
    """

    field: str
    kind: str
    decisions: int = 0
    answered: int = 0
    agreed: int = 0
    unsure: int = 0
    unsure_unstated: int = 0
    missing: int = 0
    blank: int = 0
    reasons_missing: int = 0
    problems: Counter = dataclasses.field(default_factory=Counter)
    unrecognised: Counter = dataclasses.field(default_factory=Counter)
    reported: list[dict[str, str]] = dataclasses.field(default_factory=list)
    excluded: list[dict[str, str]] = dataclasses.field(default_factory=list)
    invalid: list[dict[str, str]] = dataclasses.field(default_factory=list)
    warnings: list[dict[str, str]] = dataclasses.field(default_factory=list)
    pairs: list[tuple[str, str]] = dataclasses.field(default_factory=list)
    hard: list[tuple[str, str]] = dataclasses.field(default_factory=list)
    not_hard: list[tuple[str, str]] = dataclasses.field(default_factory=list)
    sure: list[tuple[str, str]] = dataclasses.field(default_factory=list)
    disagreements: list[dict[str, str]] = dataclasses.field(default_factory=list)

    @property
    def accounted(self) -> bool:
        """Whether every decision is in exactly one category."""
        return self.decisions == self.missing + self.blank + len(self.excluded) + len(self.invalid) + self.answered

    @property
    def agreement(self) -> float | None:
        return self.agreed / self.answered if self.answered else None

    @property
    def kappa(self) -> float | None:
        """Cohen's kappa as computed, whether or not it is fit to report; see ``kappa_withheld``."""
        return cohen_kappa(self.pairs) if self.kind in ("categorical", "binary") else None

    def kappa_cautions(self) -> list[str]:
        """Why kappa is unstable here: too few pairs, or one value dominating either annotator's values."""
        if self.kind not in ("categorical", "binary") or not self.pairs:
            return []
        cautions = []
        if len(self.pairs) < KAPPA_MIN_PAIRS:
            cautions.append(f"only {len(self.pairs)} answered pairs, fewer than {KAPPA_MIN_PAIRS}")
        for which, who in ((0, "original"), (1, "second")):
            value, count = self.distribution(which).most_common(1)[0]
            if count / len(self.pairs) >= KAPPA_MAX_SHARE:
                cautions.append(f"{value} is {count} of {len(self.pairs)} {who} values")
        return cautions

    def kappa_withheld(self) -> str | None:
        """Why kappa is not reported for this field, or None when it is reported."""
        if self.kind not in ("categorical", "binary"):
            return "not computed for this kind of field"
        if not self.pairs:
            return "no answered pairs"
        cautions = self.kappa_cautions()
        if cautions:
            return "; ".join(cautions)
        if self.kappa is None:
            return "both annotators used a single value, so chance agreement is certain"
        return None

    @property
    def reported_kappa(self) -> float | None:
        """Kappa only where it is stable enough to report."""
        return None if self.kappa_withheld() else self.kappa

    def confusion(self) -> Counter:
        """How often each original value met each second value."""
        return Counter(self.pairs)

    def label_counts(self) -> dict[str, tuple[int, int, int]]:
        """For multi-label fields: per label, how often both, only the original or only the second annotator used it."""
        if self.kind != "multi_label":
            return {}
        labels = sorted({label for pair in self.pairs for value in pair for label in _labels(value)})
        return {
            label: (
                sum(1 for a, b in self.pairs if label in _labels(a) and label in _labels(b)),
                sum(1 for a, b in self.pairs if label in _labels(a) and label not in _labels(b)),
                sum(1 for a, b in self.pairs if label not in _labels(a) and label in _labels(b)),
            )
            for label in labels
        }

    def distribution(self, which: int) -> Counter:
        return Counter(pair[which] for pair in self.pairs)

    def specific(self) -> dict[str, float | None]:
        """For binary fields, agreement on each value separately; for multi-label fields, on each label."""
        if self.kind == "binary":
            return {value: specific_agreement(self.pairs, value) for value in BOOLEAN}
        if self.kind == "multi_label":
            labels = sorted({label for pair in self.pairs for value in pair for label in _labels(value)})
            per_label = [
                [("1" if label in _labels(a) else "0", "1" if label in _labels(b) else "0") for a, b in self.pairs]
                for label in labels
            ]
            return {label: specific_agreement(pairs, "1") for label, pairs in zip(labels, per_label, strict=True)}
        return {}

    @property
    def mean_jaccard(self) -> float | None:
        if self.kind != "multi_label" or not self.pairs:
            return None
        return sum(_jaccard(a, b) for a, b in self.pairs) / len(self.pairs)

    @property
    def presence_agreement(self) -> float | None:
        """For date fields: whether both give a date, or both say none, whatever the date."""
        if self.kind != "date" or not self.pairs:
            return None
        return sum(1 for a, b in self.pairs if (a == NONE) == (b == NONE)) / len(self.pairs)


def _agreement(pairs: list[tuple[str, str]]) -> str:
    if not pairs:
        return "n/a (0)"
    return f"{sum(1 for a, b in pairs if a == b) / len(pairs):.2f} ({len(pairs)})"


def _decision(row: dict[str, str]) -> str:
    return (row.get("decision") or "").strip()


class AnswersUnreadable(Exception):
    """An answers file that cannot be read as UTF-8 CSV."""


class TableUnreadable(Exception):
    """A key or a packet's decisions file that cannot be read, or lacks a column the scorer needs."""


KEY_REQUIRED = ("decision", "decision_id", "field", "value", "hard_case")
PACKET_REQUIRED = ("decision", "field", "kind", "allowed", "multiple")


def read_table(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    """A key or a packet's decisions, read strictly. Raises ``TableUnreadable`` rather than a traceback."""
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            rows = list(reader)
    except FileNotFoundError as error:
        raise TableUnreadable(f"{path} does not exist") from error
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise TableUnreadable(f"{path} cannot be read as UTF-8 CSV: {error}") from error
    absent = [column for column in required if column not in (reader.fieldnames or [])]
    if absent:
        raise TableUnreadable(f"{path} has no column {', '.join(absent)}")
    if any(None in row for row in rows):
        raise TableUnreadable(f"{path} has lines with more cells than its header")
    return rows


def read_answers(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """An answers file's header and lines. Raises ``AnswersUnreadable`` rather than guess an encoding."""
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except FileNotFoundError as error:
        raise AnswersUnreadable(f"{path} does not exist") from error
    except UnicodeDecodeError as error:
        raise AnswersUnreadable(
            f"{path} is not UTF-8 text (byte {error.start}); ask for it to be saved as CSV in UTF-8"
        ) from error
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        rows = list(reader)
    except csv.Error as error:
        raise AnswersUnreadable(f"{path} is not readable as CSV: {error}") from error
    return list(reader.fieldnames or []), rows


def submission_errors(
    key: list[dict[str, str]],
    answers: list[dict[str, str]],
    packet: list[dict[str, str]],
    columns: list[str] | None = None,
) -> list[str]:
    """Faults that stop a submission being scored reliably. Any one of them means no scores are reported.

    A file with a line for every decision and every value blank is not faulty: it is scored as wholly unanswered.
    """
    if columns is None:
        columns = list(answers[0]) if answers else []
    errors = []
    if not columns:
        errors.append("the answers file is empty: it has no header line")
    else:
        absent = [column for column in ANSWER_COLUMNS if column not in columns]
        if absent:
            errors.append(f"the answers file has no column {', '.join(absent)}")
        if not answers:
            errors.append(f"the answers file has a header but no lines; it should have {len(key)}")
    overlong = sum(1 for row in answers if None in row)
    if overlong:
        errors.append(f"{overlong} answer lines have more cells than the header")
    counts = Counter(_decision(row) for row in answers)
    repeated = sorted(decision for decision, count in counts.items() if count > 1 and decision)
    if repeated:
        errors.append(
            f"{len(repeated)} decisions appear on more than one line, and none of their lines is chosen: "
            + ", ".join(repeated[:10])
        )
    known = {row["decision"]: row["field"] for row in key}
    if counts.get(""):
        errors.append(f"{counts['']} answer lines have no decision id")
    outside = sorted(decision for decision in counts if decision and decision not in known)
    if outside:
        errors.append(f"{len(outside)} answer lines name decisions not in the key: {', '.join(outside[:10])}")
    unnamed = sorted(
        _decision(row) for row in answers if _decision(row) in known and not (row.get("field") or "").strip()
    )
    if unnamed:
        errors.append(
            f"{len(unnamed)} answer lines have no field, so their alignment cannot be checked: "
            + ", ".join(unnamed[:10])
        )
    moved = sorted(
        _decision(row)
        for row in answers
        if _decision(row) in known and (row.get("field") or "").strip() not in ("", known[_decision(row)])
    )
    if moved:
        errors.append(f"{len(moved)} answer lines name a field other than the key's: {', '.join(moved[:10])}")
    fields = {row["decision"]: row.get("field") for row in packet}
    absent_lines = [decision for decision in known if decision not in fields]
    stray = [decision for decision, field in known.items() if decision in fields and fields[decision] != field]
    if absent_lines or stray or len(fields) != len(known):
        errors.append(
            f"the packet does not match the key: {len(absent_lines)} key decisions are not in it, {len(stray)} name "
            f"another field, and it has {len(fields)} decisions to the key's {len(known)}; check that both come from "
            "the same round"
        )
    return errors


def score(key: list[dict[str, str]], answers: list[dict[str, str]], packet: list[dict[str, str]]) -> list[FieldScore]:
    """Agreement between the key and a second annotator, for each field separately.

    Each decision is put in one category (see ``FieldScore``), and only answered decisions enter agreement. A
    decision answered more than once is never resolved by choosing a line. Check ``submission_errors`` first: when it
    reports anything, these scores must not be read.
    """
    lines = {row["decision"]: row for row in packet}
    counts = Counter(_decision(row) for row in answers)
    given = {_decision(row): row for row in answers if counts[_decision(row)] == 1}
    scores: dict[str, FieldScore] = {}
    for row in key:
        line = lines.get(row["decision"], {})
        kind = line.get("kind") or FIELD_KINDS.get(row["field"], "categorical")
        multiple = line.get("multiple") == "true" or kind == "multi_label"
        result = scores.setdefault(row["field"], FieldScore(row["field"], kind))
        result.decisions += 1
        decision_id = row.get("decision_id") or row["decision"]
        if counts[row["decision"]] > 1:
            why = f"answered on {counts[row['decision']]} lines; no line is chosen"
            result.invalid.append({"decision": decision_id, "value": "", "why": why})
            continue
        answer = given.get(row["decision"])
        if answer is None:
            result.missing += 1
            continue
        named = (answer.get("field") or "").strip()
        if named and named != row["field"]:
            result.invalid.append(
                {"decision": decision_id, "value": answer.get("value") or "", "why": f"line names {named}"}
            )
            continue
        problem = (answer.get("problem") or "").strip().lower()
        reason = (answer.get("reason") or "").strip()
        value = (answer.get("value") or "").strip()
        unsure_text = (answer.get("unsure") or "").strip().lower()
        warnings = []
        if unsure_text not in ("", *BOOLEAN):
            warnings.append(f"unsure is {unsure_text!r}, read as not stated")
        if (bool(problem) or not value or unsure_text == "true" or row.get("hard_case") == "true") and not reason:
            result.reasons_missing += 1
        if problem:
            result.reported.append({"decision": decision_id, "problem": problem, "reason": reason})
            if problem not in PROBLEMS:
                result.unrecognised[problem] += 1
                why = f"unrecognised problem code {problem!r}; exactly one of {', '.join(PROBLEMS)} is accepted"
                result.invalid.append({"decision": decision_id, "value": value, "why": why})
                continue
            result.problems[problem] += 1
            if problem in EXCLUDING or not value:
                why = f"{problem} reported" + ("; the value given with it is not scored" if value else "")
                result.excluded.append({"decision": decision_id, "value": value, "why": why})
                continue
            if unsure_text != "true":
                warnings.append(f"{INTERPRET} with a value, but unsure is not true")
        if not value:
            result.blank += 1
            if warnings:
                result.warnings.append({"decision": decision_id, "value": "", "why": "; ".join(warnings)})
            continue
        error = answer_error(value, kind, line.get("allowed", ""), multiple)
        if error:
            result.invalid.append({"decision": decision_id, "value": value, "why": error})
            continue
        second = normalise_answer(value, multiple).lower() if kind != "date" else normalise_answer(value, False)
        pair = (row["value"], second)
        result.answered += 1
        if warnings:
            result.warnings.append({"decision": decision_id, "value": value, "why": "; ".join(warnings)})
        result.pairs.append(pair)
        (result.hard if row.get("hard_case") == "true" else result.not_hard).append(pair)
        if unsure_text == "true":
            result.unsure += 1
        elif unsure_text == "false":
            result.sure.append(pair)
        else:
            result.unsure_unstated += 1
        if second == row["value"]:
            result.agreed += 1
        else:
            result.disagreements.append(
                {
                    "decision": decision_id,
                    "original": row["value"],
                    "second": second,
                    "unsure": answer.get("unsure") or "",
                    "reason": reason,
                }
            )
    return [scores[name] for name in sorted(scores)]


def render_scores(scores: list[FieldScore]) -> str:
    """Counts first, then agreement field by field, with the statistics each kind of field allows, and every
    disagreement. Nothing is pooled across fields, and kappa is printed only where it is stable enough to read."""

    def number(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.2f}"

    def kappa(s: FieldScore) -> str:
        withheld = s.kappa_withheld()
        if s.kind not in ("categorical", "binary"):
            return "n/a"
        return f"not reported: {withheld}" if withheld else number(s.reported_kappa)

    def other(s: FieldScore) -> str:
        if s.kind == "multi_label":
            return f"mean Jaccard {number(s.mean_jaccard)}"
        if s.kind == "date":
            return f"date given or none: {number(s.presence_agreement)}"
        return "-"

    answered = sum(s.answered for s in scores)
    lines = []
    if not answered:
        lines += [
            f"**No answers were supplied.** Of {sum(s.decisions for s in scores)} decisions, "
            f"{sum(s.blank for s in scores)} are blank, {sum(s.missing for s in scores)} missing, "
            f"{sum(len(s.excluded) for s in scores)} excluded by a reported problem and "
            f"{sum(len(s.invalid) for s in scores)} not scorable. No agreement statistic is reported.",
            "",
        ]
    warnings = [entry for s in scores for entry in s.warnings]
    if warnings:
        lines += [
            f"**Warnings: {len(warnings)} lines to raise with the reviewer before adjudication.** Their values, "
            "if any, are scored, but the lines do not follow the guide.",
            "",
            "| decision | value | warning |",
            "|---|---|---|",
            *(f"| {e['decision']} | {e['value']} | {e['why']} |" for e in warnings),
            "",
        ]
    lines += [
        "| field | kind | decisions | missing | blank | excluded: problem reported | excluded: not scorable "
        "| answered | unsure | unsure not stated | warnings | reason missing | agreed | raw agreement | kappa "
        "| other statistic | hard cases | not hard | sure only |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        *(
            f"| {s.field} | {s.kind} | {s.decisions} | {s.missing} | {s.blank} | {len(s.excluded)} | "
            f"{len(s.invalid)} | {s.answered} | {s.unsure} | {s.unsure_unstated} | {len(s.warnings)} | "
            f"{s.reasons_missing} | {s.agreed} | {number(s.agreement)} | {kappa(s)} | {other(s)} | "
            f"{_agreement(s.hard)} | {_agreement(s.not_hard)} | {_agreement(s.sure)} |"
            for s in scores
        ),
        "",
        "Each decision is counted once: missing (no line), blank (a line with no value and no problem code), "
        "excluded by a reported problem, excluded as not scorable, or answered. Only answered decisions enter "
        "agreement; nothing else is a negative answer or a disagreement. Agreement is raw agreement over answered "
        "pairs, with the number of pairs in brackets in the last three columns.",
        "",
        f"Kappa is computed only for categorical and binary fields, and is not reported when there are fewer than "
        f"{KAPPA_MIN_PAIRS} answered pairs, when one value is at least {KAPPA_MAX_SHARE:.0%} of either annotator's "
        "values, or when both used a single value. A field whose kappa is not reported is not thereby shown to "
        "agree poorly: read its raw agreement, marginal counts and cross-tabulation below.",
        "",
        "For multi-label fields, raw agreement is exact agreement on the whole set of labels: a pair counts only if "
        "both annotators chose the same labels, and none matches only none. It does not show partial agreement, "
        "which the mean Jaccard index (shared labels over labels used by either) and the per-label counts do, and "
        "neither is corrected for chance. Date fields are compared exactly, with agreement on whether a date is "
        "given at all shown beside it.",
        "",
        "These are statistics for each field of the decisions in this packet only. They are not pooled, and they "
        "are not an estimate of reliability for annotations outside the packet.",
    ]
    for s in scores:
        if not s.pairs:
            continue
        original = ", ".join(f"{value} {count}" for value, count in sorted(s.distribution(0).items()))
        second = ", ".join(f"{value} {count}" for value, count in sorted(s.distribution(1).items()))
        lines += [
            "",
            f"**{s.field}**",
            "",
            f"- answered pairs: {len(s.pairs)}; agreed: {s.agreed}; raw agreement: {number(s.agreement)}",
            f"- original values: {original}",
            f"- second values: {second}",
        ]
        if s.kind in ("categorical", "binary"):
            lines.append(
                "- original → second: "
                + ", ".join(f"{a} → {b} {count}" for (a, b), count in sorted(s.confusion().items()))
            )
            lines.append(f"- kappa: {kappa(s)}")
        specific = s.specific()
        counts = s.label_counts()
        if specific:
            lines.append(
                "- agreement on each value: "
                + ", ".join(
                    f"{value} {number(rate)}"
                    + (
                        f" (both {counts[value][0]}, original only {counts[value][1]}, second only {counts[value][2]})"
                        if value in counts
                        else ""
                    )
                    for value, rate in specific.items()
                )
            )
    by_code = [s for s in scores if s.problems or s.unrecognised]
    if by_code:
        codes = [code for code in PROBLEMS if any(s.problems.get(code) for s in by_code)]
        lines += ["", "Problem codes reported, by field:", ""]
        lines += [
            "| field | " + " | ".join(codes + ["unrecognised"]) + " |",
            "|---|" + "---|" * (len(codes) + 1),
            *(
                f"| {s.field} | "
                + " | ".join([str(s.problems.get(code, 0)) for code in codes] + [str(sum(s.unrecognised.values()))])
                + " |"
                for s in by_code
            ),
        ]
    for title, entries in (
        ("Excluded by a reported problem", [e for s in scores for e in s.excluded]),
        ("Excluded as not scorable", [e for s in scores for e in s.invalid]),
    ):
        if entries:
            lines += ["", f"{title}:", "", "| decision | value | why |", "|---|---|---|"]
            lines += [f"| {e['decision']} | {e['value']} | {e['why']} |" for e in entries]
    reported = [r for s in scores for r in s.reported]
    if reported:
        lines += ["", "Problems the annotator reported:", "", "| decision | problem | reason |", "|---|---|---|"]
        lines += [f"| {r['decision']} | {r['problem']} | {r['reason']} |" for r in reported]
    disagreements = [d for s in scores for d in s.disagreements]
    if disagreements:
        lines += [
            "",
            "Disagreements:",
            "",
            "| decision | original | second | unsure | reason |",
            "|---|---|---|---|---|",
        ]
        lines += [
            f"| {d['decision']} | {d['original']} | {d['second']} | {d['unsure']} | {d['reason']} |"
            for d in disagreements
        ]
    return "\n".join(lines) + "\n"


def latest_reviews(reviews: Iterable[AnnotationReview]) -> dict[str, AnnotationReview]:
    """The latest review of each decision."""
    latest: dict[str, AnnotationReview] = {}
    for review in sorted(reviews, key=lambda r: (r.adjudicated_on or r.annotated_on, r.annotated_on)):
        latest[review.decision] = review
    return latest


def reviewed_records(dataset: Dataset) -> set[str]:
    """Records every one of whose decisions a person's review has settled."""
    settled = {decision for decision, review in latest_reviews(dataset.reviews).items() if review.settled is not None}
    by_record: dict[str, set[str]] = defaultdict(set)
    for decision in decisions(dataset):
        by_record[decision.record].add(decision.id)
    return {record for record, ids in by_record.items() if ids <= settled}


def review_problems(dataset: Dataset) -> Iterator[tuple[str, str]]:
    """Reviews that do not match the dataset, and records marked reviewed without a settled review by a person."""
    current = {decision.id: decision for decision in decisions(dataset)}
    for decision_id, review in latest_reviews(dataset.reviews).items():
        where = f"review of {decision_id}"
        decision = current.get(decision_id)
        if decision is None:
            yield where, "reviews a decision the dataset does not hold"
            continue
        settled = review.settled
        if settled is not None and decision.value != settled:
            yield where, f"settled on {settled!r}, but the record holds {decision.value!r}"
        elif settled is None and decision.value != review.original:
            yield (
                where,
                f"the record holds {decision.value!r}, but the review awaits adjudication of {review.original!r}",
            )
    reviewed = reviewed_records(dataset)
    for provision in dataset.provisions.values():
        if provision.annotation_reviewed and provision.id not in reviewed:
            yield (
                f"provision {provision.id}",
                "is marked annotation_reviewed, but a person's review has not settled every one of its decisions",
            )
