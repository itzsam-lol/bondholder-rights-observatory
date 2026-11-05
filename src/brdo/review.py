"""Materials for a blind second annotation, and the rules that keep a review honest.

A packet lists each judgement to be made again: the document and page it rests on, a locator, the passage the record
quotes, the allowed values and the rule of ``docs/annotation-codebook.md`` that applies. It never gives the current
value. Hard cases are flagged from the source text alone, with a note that says what makes them hard and not what to
choose. The key, which holds the current values, is written to a separate directory.

``score`` compares a second annotator's answers with the key, field by field and never pooled, with raw agreement,
Cohen's kappa and every disagreement.

Nothing here marks an annotation as reviewed. A review is an ``AnnotationReview`` in ``data/annotation-reviews.yaml``,
made by a person other than the original annotator, keeping the original, second and adjudicated values and the
reasons for them. Re-applying the same rules, the same curator re-reading, or another pass by an automated process is
not a review and must not be recorded as one. ``review_problems`` enforces what the records can show of this.
"""

from __future__ import annotations

import csv
import dataclasses
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
BOOLEAN = ("true", "false")
DATE_OR_BLANK = "a date as YYYY-MM-DD, or blank"

PACKET_COLUMNS = [
    "decision",
    "field",
    "allowed",
    "multiple",
    "document",
    "url",
    "page",
    "locator",
    "passage",
    "hard_case",
    "hard_case_note",
    "rule",
]
ANSWER_COLUMNS = ["decision", "field", "value", "unsure", "reason"]
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
        return "|".join(sorted({part.strip().lower() for part in text.split("|") if part.strip()}))
    return text.strip().lower() if text.strip().lower() in BOOLEAN else text.strip()


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

    def packet_row(self, packet_id: str) -> dict[str, object]:
        """The line a packet gives the annotator: no value, and an id for this round instead of the record's own."""
        return {
            "decision": packet_id,
            "field": self.field,
            "allowed": self.allowed,
            "multiple": "true" if self.multiple else "false",
            "document": self.document,
            "url": self.url,
            "page": "" if self.page is None else self.page,
            "locator": self.locator,
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
                    allowed=_choices(ActionKind),
                    multiple=True,
                    value=canonical([action.kind for action in row.actions]),
                    document=report.document,
                    url=url(report.document),
                    page=row.page,
                    locator=f"{printed}, action columns",
                    passage=" / ".join(f"{name}: {text}" for name, text in action_cells if text),
                    rule="annotation-codebook.md#actions",
                )
            )
            out.append(
                Decision(
                    id=f"{row_id}:carried_over_from",
                    field="breach_row.carried_over_from",
                    record=row_id,
                    allowed=DATE_OR_BLANK,
                    multiple=False,
                    value=canonical(row.carried_over_from),
                    document=report.document,
                    url=url(report.document),
                    page=row.page,
                    locator=f"{printed}, its label",
                    passage="",
                    rule="annotation-codebook.md#carried-over-breaches",
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
                        )
                    )

    for notice in sorted(dataset.breach_notices.values(), key=lambda n: n.id):
        passage = notice.covenant_as_reported or notice.deed_as_reported or ""
        for name, allowed, value in (
            ("kind", _choices(NoticeKind), notice.kind),
            ("period_end", DATE_OR_BLANK, notice.period_end),
            ("adjourned_for_lack_of_quorum", "|".join(BOOLEAN), notice.adjourned_for_lack_of_quorum),
        ):
            out.append(
                Decision(
                    id=f"{notice.id}:{name}",
                    field=f"notice.{name}",
                    record=notice.id,
                    allowed=allowed,
                    multiple=False,
                    value=canonical(value),
                    document=notice.document,
                    url=url(notice.document),
                    page=notice.page,
                    locator=f"letter dated {notice.issued_on.isoformat()}",
                    passage=passage,
                    rule="annotation-codebook.md#letters",
                )
            )

    for statement in sorted(dataset.compliance_statements.values(), key=lambda s: s.id):
        passage = " / ".join(item.quote for item in statement.evidence if item.quote)
        page = next((item.page for item in statement.evidence if item.page is not None), None)
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
                    locator=f"statement for {statement.period.start.isoformat()} to {statement.period.end.isoformat()}",
                    passage=passage,
                    rule="annotation-codebook.md#compliance-statements",
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
                    hard_case_note=_hard_case(field_name, provision.text, provision),
                )
            )
    return out


def _write_csv(path: Path, columns: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


INSTRUCTIONS = """Second annotation packet

Read codebook.md, then SEBI's Annex-VIA it points to, before starting. For each line of decisions.csv, open the
document at the page given, read the passage in its context, and fill in the matching line of answers.csv: a value
from the allowed list (several separated by | where multiple is true), unsure as true or false, and a reason for every
hard case and every decision you are unsure about. Leave a value blank, with a reason, if the source does not let you
decide.

Do not look at the project's data, exports or reports until you have handed in your answers.

Codebook commit: {commit}
Decisions: {count}
"""


def write_packet(
    dataset: Dataset, directory: Path, codebook: Path, commit: str, fields: set[str] | None = None
) -> dict:
    """Write the packet for the annotator and, apart from it, the key.

    Packet lines carry ids for this round only (``D0001``...), because record ids are the curator's and could hint
    at a value. The key maps them to the stable decision ids that review records use.
    """
    chosen = [d for d in decisions(dataset) if fields is None or d.field in fields]
    ids = [f"D{number:04d}" for number in range(1, len(chosen) + 1)]
    packet, key = directory / "packet", directory / "key"
    _write_csv(packet / "decisions.csv", PACKET_COLUMNS, (d.packet_row(i) for i, d in zip(ids, chosen, strict=True)))
    _write_csv(
        packet / "answers.csv",
        ANSWER_COLUMNS,
        (
            {"decision": i, "field": d.field, "value": "", "unsure": "", "reason": ""}
            for i, d in zip(ids, chosen, strict=True)
        ),
    )
    (packet / "codebook.md").write_text(codebook.read_text(encoding="utf-8"), encoding="utf-8")
    (packet / "README.txt").write_text(INSTRUCTIONS.format(commit=commit, count=len(chosen)), encoding="utf-8")
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


@dataclass
class FieldScore:
    field: str
    decisions: int = 0
    answered: int = 0
    agreed: int = 0
    pairs: list[tuple[str, str]] = dataclasses.field(default_factory=list)
    disagreements: list[dict[str, str]] = dataclasses.field(default_factory=list)

    @property
    def agreement(self) -> float | None:
        return self.agreed / self.answered if self.answered else None

    @property
    def kappa(self) -> float | None:
        return cohen_kappa(self.pairs)


def score(key: list[dict[str, str]], answers: list[dict[str, str]], packet: list[dict[str, str]]) -> list[FieldScore]:
    """Agreement between the key and a second annotator, for each field separately.

    A blank answer is counted as unanswered, not as a disagreement. Answers to decisions not in the key are ignored.
    """
    multiple = {row["decision"]: row["multiple"] == "true" for row in packet}
    given = {row["decision"]: row for row in answers}
    scores: dict[str, FieldScore] = {}
    for row in key:
        result = scores.setdefault(row["field"], FieldScore(row["field"]))
        result.decisions += 1
        answer = given.get(row["decision"])
        if answer is None or not answer.get("value", "").strip():
            continue
        second = normalise_answer(answer["value"], multiple.get(row["decision"], False))
        result.answered += 1
        result.pairs.append((row["value"], second))
        if second == row["value"]:
            result.agreed += 1
        else:
            result.disagreements.append(
                {
                    "decision": row.get("decision_id") or row["decision"],
                    "original": row["value"],
                    "second": second,
                    "reason": answer.get("reason", ""),
                }
            )
    return [scores[name] for name in sorted(scores)]


def render_scores(scores: list[FieldScore]) -> str:
    def number(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.2f}"

    lines = [
        "| field | decisions | answered | agreed | agreement | kappa |",
        "|---|---|---|---|---|---|",
        *(
            f"| {s.field} | {s.decisions} | {s.answered} | {s.agreed} | {number(s.agreement)} | {number(s.kappa)} |"
            for s in scores
        ),
    ]
    disagreements = [d for s in scores for d in s.disagreements]
    if disagreements:
        lines += ["", "| decision | original | second | reason |", "|---|---|---|---|"]
        lines += [f"| {d['decision']} | {d['original']} | {d['second']} | {d['reason']} |" for d in disagreements]
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
