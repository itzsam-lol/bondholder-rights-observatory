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
        passage = notice.covenant_as_reported or notice.deed_as_reported or ""
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
                    passage=passage,
                    rule="annotation-codebook.md#letters",
                    isins=tuple(notice.isins),
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
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


INSTRUCTIONS = """Second annotation packet

Read codebook.md, then SEBI's Annex-VIA it points to, before starting. For each line of decisions.csv, open the
document at the address given, check that its SHA-256 matches, go to the page and read the passage in its context.
Then fill in the matching line of answers.csv:

- value: one of the allowed values (several separated by | where multiple is true). Write none where the allowed
  values say so, for example when a letter states no quarter. Leave the value blank only if the source does not let
  you decide, and say why.
- unsure: true or false.
- reason: required for every hard case, every decision marked unsure, and every blank value.

Do not look at the project's data, exports or reports until you have handed in your answers. The answer key is not
in this folder and must not be sent with it.

Codebook commit: {commit}
Round: {round}
Decisions: {count}
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
            {"decision": i, "field": d.field, "value": "", "unsure": "", "reason": ""}
            for i, d in zip(ids, chosen, strict=True)
        ),
    )
    (packet / "codebook.md").write_text(codebook.read_text(encoding="utf-8"), encoding="utf-8")
    (packet / "README.txt").write_text(
        INSTRUCTIONS.format(commit=commit, round=chosen_round, count=len(chosen)), encoding="utf-8"
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


@dataclass
class FieldScore:
    """Agreement on one field. Fields are never pooled."""

    field: str
    kind: str
    decisions: int = 0
    answered: int = 0
    agreed: int = 0
    unsure: int = 0
    pairs: list[tuple[str, str]] = dataclasses.field(default_factory=list)
    hard: list[tuple[str, str]] = dataclasses.field(default_factory=list)
    sure: list[tuple[str, str]] = dataclasses.field(default_factory=list)
    disagreements: list[dict[str, str]] = dataclasses.field(default_factory=list)

    @property
    def agreement(self) -> float | None:
        return self.agreed / self.answered if self.answered else None

    @property
    def kappa(self) -> float | None:
        """Only for categorical and binary fields. Exact-set and date agreement are not chance-corrected here."""
        return cohen_kappa(self.pairs) if self.kind in ("categorical", "binary") else None

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


def score(key: list[dict[str, str]], answers: list[dict[str, str]], packet: list[dict[str, str]]) -> list[FieldScore]:
    """Agreement between the key and a second annotator, for each field separately.

    A blank answer is counted as unanswered, not as a disagreement. Answers to decisions not in the key are ignored.
    Hard cases and decisions the annotator marked unsure are also scored apart, so that they can be read alone.
    """
    lines = {row["decision"]: row for row in packet}
    given = {row["decision"]: row for row in answers}
    scores: dict[str, FieldScore] = {}
    for row in key:
        line = lines.get(row["decision"], {})
        kind = line.get("kind") or FIELD_KINDS.get(row["field"], "categorical")
        result = scores.setdefault(row["field"], FieldScore(row["field"], kind))
        result.decisions += 1
        answer = given.get(row["decision"])
        if answer is None or not answer.get("value", "").strip():
            continue
        second = normalise_answer(answer["value"], line.get("multiple") == "true")
        pair = (row["value"], second)
        result.answered += 1
        result.pairs.append(pair)
        if row.get("hard_case") == "true":
            result.hard.append(pair)
        if answer.get("unsure", "").strip().lower() == "true":
            result.unsure += 1
        else:
            result.sure.append(pair)
        if second == row["value"]:
            result.agreed += 1
        else:
            result.disagreements.append(
                {
                    "decision": row.get("decision_id") or row["decision"],
                    "original": row["value"],
                    "second": second,
                    "unsure": answer.get("unsure", ""),
                    "reason": answer.get("reason", ""),
                }
            )
    return [scores[name] for name in sorted(scores)]


def render_scores(scores: list[FieldScore]) -> str:
    """Counts first, then agreement, with the statistic each kind of field allows, and every disagreement."""

    def number(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.2f}"

    def statistic(s: FieldScore) -> str:
        if s.kind in ("categorical", "binary"):
            return f"kappa {number(s.kappa)}"
        if s.kind == "multi_label":
            return f"mean Jaccard {number(s.mean_jaccard)}"
        return f"date given or none: {number(s.presence_agreement)}"

    lines = [
        "| field | kind | decisions | answered | unsure | agreed | raw agreement | statistic | hard cases "
        "| sure only |",
        "|---|---|---|---|---|---|---|---|---|---|",
        *(
            f"| {s.field} | {s.kind} | {s.decisions} | {s.answered} | {s.unsure} | {s.agreed} | "
            f"{number(s.agreement)} | {statistic(s)} | {_agreement(s.hard)} | {_agreement(s.sure)} |"
            for s in scores
        ),
        "",
        "Raw agreement for multi-label fields is exact agreement on the whole set. Kappa is shown only for "
        "categorical and binary fields, and is unstable when a value is rare: read it with the distributions below.",
    ]
    for s in scores:
        if not s.pairs:
            continue
        original = ", ".join(f"{value or 'blank'} {count}" for value, count in sorted(s.distribution(0).items()))
        second = ", ".join(f"{value or 'blank'} {count}" for value, count in sorted(s.distribution(1).items()))
        lines += ["", f"**{s.field}**", "", f"- original values: {original}", f"- second values: {second}"]
        specific = s.specific()
        if specific:
            lines.append(
                "- agreement on each value: " + ", ".join(f"{value} {number(rate)}" for value, rate in specific.items())
            )
    disagreements = [d for s in scores for d in s.disagreements]
    if disagreements:
        lines += ["", "| decision | original | second | unsure | reason |", "|---|---|---|---|---|"]
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
