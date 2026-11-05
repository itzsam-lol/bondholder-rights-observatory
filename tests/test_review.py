"""Blind second-annotation materials, agreement scoring, and the rules that keep a review honest."""

import re
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from brdo.models import AnnotationReview, BreachItem, Provision
from brdo.pit import as_of
from brdo.review import (
    KEY_COLUMNS,
    PACKET_COLUMNS,
    PacketRefused,
    canonical,
    cohen_kappa,
    decisions,
    normalise_answer,
    read_csv,
    render_scores,
    review_problems,
    round_fields,
    score,
    write_packet,
)
from brdo.store import Severity, check_integrity
from brdo.vocab import AvailabilityMode, CovenantCategory, CovenantSpecificity, ProvisionStage, ReviewerKind
from tests.conftest import ISIN_LISTED, make_document, make_report, make_row

REPOSITORY = Path(__file__).resolve().parents[1]


def _codebook(tmp_path: Path) -> Path:
    path = tmp_path / "codebook.md"
    path.write_text("# Codebook\n", encoding="utf-8")
    return path


def _review(decision: str, original: str, second: str, **overrides) -> AnnotationReview:
    values = dict(
        decision=decision,
        codebook_commit="abcdef0",
        original=original,
        original_annotator="curator",
        second=second,
        second_annotator="annotator-b",
        second_by=ReviewerKind.PERSON,
        annotated_on=date(2026, 12, 1),
    )
    return AnnotationReview(**(values | overrides))


def _provision(**overrides) -> Provision:
    values = dict(
        id="p",
        document="report-q1",
        clause="1",
        page=1,
        text="maintain a ratio of less than 5%",
        instruments=[ISIN_LISTED],
        category=CovenantCategory.FINANCIAL,
    )
    return Provision(**(values | overrides))


def _with_item(dataset, text: str, levels: list[str] | None = None):
    row = make_row()
    item = row.items[0].model_copy(update={"covenant_as_reported": text, "levels_stated": levels or []})
    dataset.breach_reports["report-q1"] = make_report(rows=[row.model_copy(update={"items": [item]})])
    return dataset


def test_a_packet_never_carries_the_current_value_or_the_curators_record_ids(dataset, tmp_path):
    dataset.provisions["p"] = _provision()
    written = write_packet(dataset, tmp_path / "round", _codebook(tmp_path), "abcdef0")
    packet = read_csv(written["packet"] / "decisions.csv")
    answers = read_csv(written["packet"] / "answers.csv")
    key = read_csv(written["key"] / "key.csv")

    assert list(packet[0]) == PACKET_COLUMNS and "value" not in PACKET_COLUMNS and "record" not in PACKET_COLUMNS
    assert list(key[0]) == KEY_COLUMNS
    assert all(row["decision"].startswith("D") and row["decision"][1:].isdigit() for row in packet)
    assert (
        [row["decision"] for row in packet] == [row["decision"] for row in answers] == [row["decision"] for row in key]
    )
    assert all(row["value"] == "" for row in answers)
    record_ids = {row["record"] for row in key} | {row["decision_id"] for row in key}
    assert not [cell for row in packet for cell in row.values() if cell in record_ids]
    assert not (written["packet"] / "key.csv").exists()
    by_field = {row["field"]: row["value"] for row in key}
    assert by_field["breach_item.category"] == "financial" and by_field["provision.stage"] == "described_in_force"


def test_a_packet_can_be_limited_to_some_fields(dataset, tmp_path):
    written = write_packet(dataset, tmp_path / "round", _codebook(tmp_path), "abcdef0", {"breach_item.category"})
    assert {row["field"] for row in read_csv(written["packet"] / "decisions.csv")} == {"breach_item.category"}


def test_every_annotated_field_becomes_a_decision(dataset):
    dataset.provisions["p"] = _provision()
    fields = {decision.field for decision in decisions(dataset)}
    assert {
        "breach_item.category",
        "breach_item.specificity",
        "breach_item.assignment_uncertain",
        "breach_row.actions",
        "breach_row.carried_over_from",
        "provision.category",
        "provision.stage",
    } <= fields


def test_a_split_printed_row_gives_distinct_decisions(dataset):
    dataset.breach_reports["report-q1"] = make_report(rows=[make_row(), make_row()])
    ids = [decision.id for decision in decisions(dataset)]
    assert len(ids) == len(set(ids))
    assert any(":row-1.1:" in i for i in ids) and any(":row-1.2:" in i for i in ids)


@pytest.mark.parametrize(
    ("text", "levels", "field"),
    [
        ("Non-Maintainance of Security cover", [], "breach_item.category"),
        ("Part B Schedule I: Security Cover Ratio - 1.10x", ["1.10x"], "breach_item.category"),
        ("The maximum permissible ratio of the sum of PAR > 30 and write-offs", [], "breach_item.specificity"),
        (
            'Breach of maximum permissible ratio of "Total Financial Indebtness:Tangible Net worth"',
            [],
            "breach_item.specificity",
        ),
        ("Delay in Listed", [], "breach_item.category"),
        ("Non Payment of Interest & principal : The Issuer is required to make payment", [], "breach_item.category"),
        ("10. Non compliance w.r.t. clause 1.4.1(vi) of Negative Covenants", [], "breach_item.category"),
    ],
)
def test_the_known_hard_cases_are_flagged_from_the_text_alone(dataset, text, levels, field):
    _with_item(dataset, text, levels)
    flagged = {d.field for d in decisions(dataset) if d.hard_case_note}
    assert field in flagged


def test_a_plain_cell_is_not_a_hard_case(dataset):
    _with_item(dataset, "(e) a Write-Off Ratio may not at any time increase above 6.5%", ["6.5%"])
    assert not [d.id for d in decisions(dataset) if d.hard_case_note]


def test_hard_case_flags_do_not_depend_on_the_current_value(dataset):
    _with_item(dataset, "Breach of Security cover")
    before = {d.id: d.hard_case_note for d in decisions(dataset)}
    report = dataset.breach_reports["report-q1"]
    row = report.rows[0]
    item = row.items[0].model_copy(
        update={"category": CovenantCategory.OTHER, "specificity": CovenantSpecificity.CLAUSE_NUMBER_ONLY}
    )
    dataset.breach_reports["report-q1"] = report.model_copy(update={"rows": [row.model_copy(update={"items": [item]})]})
    assert {d.id: d.hard_case_note for d in decisions(dataset)} == before


def test_a_hard_case_note_never_names_a_value_to_choose(dataset):
    for text in ("Breach of Security cover", "The maximum permissible ratio of PAR", "Delay in Listed"):
        _with_item(dataset, text)
        for decision in decisions(dataset):
            if decision.hard_case_note:
                note = decision.hard_case_note.lower()
                named = [v for v in decision.allowed.split("|") if v and v.replace("_", " ") in note]
                assert named == [], (decision.id, named)


def test_the_codebook_states_rules_without_the_current_labels():
    codebook = (REPOSITORY / "docs" / "annotation-codebook.md").read_text(encoding="utf-8")
    assert not re.search(r"\blabell?ed\s+`|\bthroughout\b|\bcurrently (?:is|are)\b", codebook, re.IGNORECASE)
    slugs = {
        re.sub(r"[^\w\- ]", "", line[3:].strip().lower()).replace(" ", "-")
        for line in codebook.splitlines()
        if line.startswith("## ")
    }
    assert {d.rule.split("#")[1] for d in decisions_of_repository()} <= slugs


def decisions_of_repository():
    from brdo.store import load_dataset

    return decisions(load_dataset(REPOSITORY / "data"))


def test_kappa_matches_a_hand_computation():
    pairs = [("a", "a"), ("a", "b"), ("b", "b"), ("b", "b")]
    assert cohen_kappa(pairs) == pytest.approx(0.5)
    assert cohen_kappa([("a", "a"), ("b", "b")]) == pytest.approx(1.0)
    assert cohen_kappa([("a", "a"), ("a", "a")]) is None
    assert cohen_kappa([]) is None


def test_scores_are_kept_per_field_and_blanks_are_not_disagreements():
    key = [
        {"decision": "D0001", "decision_id": "x:category", "field": "breach_item.category", "value": "financial"},
        {"decision": "D0002", "decision_id": "y:category", "field": "breach_item.category", "value": "other"},
        {
            "decision": "D0003",
            "decision_id": "x:actions",
            "field": "breach_row.actions",
            "value": "awaiting_instructions|cure_reported",
        },
        {"decision": "D0004", "decision_id": "z:category", "field": "breach_item.category", "value": "other"},
    ]
    packet = [
        {"decision": row["decision"], "multiple": "true" if "actions" in row["field"] else "false"} for row in key
    ]
    answers = [
        {"decision": "D0001", "value": "financial", "reason": ""},
        {"decision": "D0002", "value": "affirmative", "reason": "an undertaking to maintain"},
        {"decision": "D0003", "value": " Cure_Reported | awaiting_instructions ", "reason": ""},
        {"decision": "D0004", "value": "  ", "reason": "cannot tell"},
    ]
    scores = {s.field: s for s in score(key, answers, packet)}
    assert set(scores) == {"breach_item.category", "breach_row.actions"}
    category = scores["breach_item.category"]
    assert (category.decisions, category.answered, category.agreed) == (3, 2, 1)
    assert category.disagreements == [
        {
            "decision": "y:category",
            "original": "other",
            "second": "affirmative",
            "unsure": "",
            "reason": "an undertaking to maintain",
        }
    ]
    assert scores["breach_row.actions"].agreed == 1


def test_canonical_values_are_stable():
    assert canonical(None) == "" and canonical(True) == "true" and canonical(date(2026, 6, 30)) == "2026-06-30"
    assert canonical([ProvisionStage.OFFERED, ProvisionStage.EXECUTED_TEXT]) == "executed_text|offered"


def test_only_a_person_other_than_the_original_annotator_can_review():
    with pytest.raises(ValidationError):
        _review("d", "financial", "financial", second_annotator="Curator ")
    with pytest.raises(ValidationError):
        _review("d", "financial", "financial", second_by="automated")
    with pytest.raises(ValidationError):
        _review("d", "financial", "other", adjudicated="other")
    with pytest.raises(ValidationError):
        _review("d", "financial", "other", adjudication_reason="because")


def test_a_review_keeps_all_three_values_apart():
    agreed = _review("d", "financial", "financial")
    pending = _review("d", "financial", "affirmative")
    settled = pending.model_copy(
        update={
            "adjudicated": "affirmative",
            "adjudicated_by": "adjudicator-c",
            "adjudication_reason": "the annex lists it among affirmative covenants",
            "adjudicated_on": date(2026, 12, 5),
        }
    )
    assert (agreed.settled, pending.settled, settled.settled) == ("financial", None, "affirmative")
    assert (settled.original, settled.second, settled.adjudicated) == ("financial", "affirmative", "affirmative")


def errors(dataset) -> list[str]:
    return [str(p) for p in check_integrity(dataset) if p.severity is Severity.ERROR]


def test_a_clause_record_cannot_be_marked_reviewed_without_a_persons_settled_review(dataset):
    dataset.provisions["p"] = _provision(annotation_reviewed=True)
    assert any("is marked annotation_reviewed" in e for e in errors(dataset))

    dataset.reviews = [_review("p:category", "financial", "financial")]
    assert any("is marked annotation_reviewed" in e for e in errors(dataset)), "the stage is not reviewed yet"

    dataset.reviews.append(_review("p:stage", "described_in_force", "offered"))
    assert any("is marked annotation_reviewed" in e for e in errors(dataset)), "a disagreement is not settled"

    dataset.reviews[-1] = dataset.reviews[-1].model_copy(
        update={
            "adjudicated": "described_in_force",
            "adjudicated_by": "adjudicator-c",
            "adjudication_reason": "a trustee's letter quoting a clause",
            "adjudicated_on": date(2026, 12, 5),
        }
    )
    assert errors(dataset) == []


def test_a_review_must_match_the_record_it_settles(dataset):
    dataset.provisions["p"] = _provision()
    dataset.reviews = [
        _review(
            "p:category",
            "financial",
            "affirmative",
            adjudicated="affirmative",
            adjudicated_by="adjudicator-c",
            adjudication_reason="listed in the annex as affirmative",
            adjudicated_on=date(2026, 12, 5),
        ),
        _review("ghost:category", "financial", "financial"),
    ]
    found = [message for _, message in review_problems(dataset)]
    assert any("settled on 'affirmative', but the record holds 'financial'" in m for m in found)
    assert any("does not hold" in m for m in found)


def test_a_view_before_the_review_does_not_count_it(dataset):
    dataset.documents["report-q1"] = make_document(retrieved_at=datetime(2026, 11, 3, 8, 0, tzinfo=UTC))
    dataset.provisions["p"] = _provision(annotation_reviewed=True)
    dataset.reviews = [
        _review("p:category", "financial", "financial"),
        _review("p:stage", "described_in_force", "described_in_force"),
    ]
    assert errors(dataset) == []
    earlier = as_of(dataset, date(2026, 11, 30), AvailabilityMode.OBSERVED)
    later = as_of(dataset, date(2026, 12, 31), AvailabilityMode.OBSERVED)
    assert earlier.reviews == [] and not earlier.provisions["p"].annotation_reviewed
    assert len(later.reviews) == 2 and later.provisions["p"].annotation_reviewed


def test_no_record_in_this_release_is_marked_reviewed():
    from brdo.store import load_dataset

    data = load_dataset(REPOSITORY / "data")
    assert data.reviews == []
    assert not [p.id for p in data.provisions.values() if p.annotation_reviewed]


def test_an_item_that_names_a_ratio_with_a_level_is_not_flagged(dataset):
    item = BreachItem(
        isins=[ISIN_LISTED],
        covenant_as_reported="maintain the debt-to-equity ratio below 4 times",
        levels_stated=["4 times"],
        page=1,
        category=CovenantCategory.FINANCIAL,
        specificity=CovenantSpecificity.CLAUSE_TEXT,
    )
    row = make_row()
    dataset.breach_reports["report-q1"] = make_report(rows=[row.model_copy(update={"items": [item]})])
    assert not [d.id for d in decisions(dataset) if d.hard_case_note]


def test_a_packet_is_refused_inside_the_repository_or_over_an_earlier_round(dataset, tmp_path):
    with pytest.raises(PacketRefused, match="inside the repository"):
        write_packet(dataset, tmp_path / "repo" / "round", _codebook(tmp_path), "abcdef0", repository=tmp_path / "repo")
    write_packet(dataset, tmp_path / "round", _codebook(tmp_path), "abcdef0", repository=tmp_path / "repo")
    with pytest.raises(PacketRefused, match="already holds"):
        write_packet(dataset, tmp_path / "round", _codebook(tmp_path), "abcdef0")


def test_the_key_is_readable_by_its_owner_only_and_never_beside_the_packet(dataset, tmp_path):
    written = write_packet(dataset, tmp_path / "round", _codebook(tmp_path), "abcdef0")
    assert written["key"].stat().st_mode & 0o777 == 0o700
    assert (written["key"] / "key.csv").stat().st_mode & 0o777 == 0o600
    assert sorted(path.name for path in written["packet"].iterdir()) == [
        "README.txt",
        "answers.csv",
        "codebook.md",
        "decisions.csv",
    ]


def test_no_export_or_document_holds_a_review_key():
    published = [
        *(REPOSITORY / "exports").iterdir(),
        *(REPOSITORY / "docs").iterdir(),
        *(REPOSITORY / "data").rglob("*"),
    ]
    assert not [path for path in published if path.name in {"key.csv", "decisions.csv", "answers.csv"}]


def test_each_packet_line_names_its_file_its_hash_its_isins_and_how_it_is_compared(dataset, tmp_path):
    dataset.provisions["p"] = _provision()
    packet = read_csv(
        write_packet(dataset, tmp_path / "round", _codebook(tmp_path), "abcdef0")["packet"] / "decisions.csv"
    )
    assert all(row["url"] and row["sha256"] and row["isins"] and row["page"] for row in packet)
    assert {row["field"]: row["kind"] for row in packet}["breach_row.actions"] == "multi_label"
    assert {row["field"]: row["kind"] for row in packet}["breach_row.carried_over_from"] == "date"


def test_a_missing_date_is_none_in_the_key_never_blank(dataset, tmp_path):
    key = read_csv(write_packet(dataset, tmp_path / "round", _codebook(tmp_path), "abcdef0")["key"] / "key.csv")
    assert {row["field"]: row["value"] for row in key}["breach_row.carried_over_from"] == "none"
    assert normalise_answer(" None ", multiple=False) == "none"
    assert normalise_answer("none", multiple=True) == "none"
    assert normalise_answer("awaiting_instructions|none", multiple=True) == "awaiting_instructions"


def test_rounds_split_the_decisions_without_looking_at_their_values(dataset):
    dataset.provisions["p"] = _provision()
    every = decisions(dataset)
    first = [d.id for d in every if round_fields(dataset, "1")(d)]
    second = [d.id for d in every if round_fields(dataset, "2")(d)]
    assert set(first) | set(second) == {d.id for d in every} and not set(first) & set(second)
    assert any(":category" in i for i in first) and any("provision" in i or ":stage" in i for i in second)
    row = dataset.breach_reports["report-q1"].rows[0]
    item = row.items[0].model_copy(update={"category": CovenantCategory.OTHER})
    dataset.breach_reports["report-q1"] = make_report(rows=[row.model_copy(update={"items": [item]})])
    assert [d.id for d in decisions(dataset) if round_fields(dataset, "1")(d)] == first


def test_round_one_covers_the_statement_comparisons_and_closure_findings_in_the_release():
    from brdo.store import load_dataset

    data = load_dataset(REPOSITORY / "data")
    first = {d.field for d in decisions(data) if round_fields(data, "1")(d)}
    assert {
        "statement.made_by",
        "statement.scope",
        "statement.breach_stated",
        "breach_row.actions",
        "notice.kind",
        "notice.period_end",
        "notice.adjourned_for_lack_of_quorum",
        "breach_item.category",
        "breach_item.specificity",
    } <= first


def test_binary_fields_report_agreement_on_each_value_and_rare_values_show():
    key = [{"decision": f"D{i}", "field": "statement.breach_stated", "value": v} for i, v in enumerate("ttttttttff")]
    key = [dict(row, value="true" if row["value"] == "t" else "false") for row in key]
    answers = [{"decision": row["decision"], "value": row["value"], "reason": ""} for row in key]
    answers[8]["value"] = "true"  # one disagreement on the rare value
    [result] = score(key, answers, [])
    assert result.kind == "binary" and result.agreed == 9
    assert result.specific()["false"] == pytest.approx(2 * 1 / (2 * 1 + 1))
    assert result.specific()["true"] == pytest.approx(2 * 8 / (2 * 8 + 1))
    assert result.kappa is not None and result.kappa < result.agreement
    assert "false 2" in render_scores([result]) and "true 9" in render_scores([result])


def test_multi_label_fields_are_scored_on_the_set_and_on_each_label():
    key = [
        {"decision": "D1", "field": "breach_row.actions", "value": "awaiting_instructions|holders_meeting_held"},
        {"decision": "D2", "field": "breach_row.actions", "value": "cure_reported"},
    ]
    packet = [
        {"decision": "D1", "multiple": "true", "kind": "multi_label"},
        {"decision": "D2", "multiple": "true", "kind": "multi_label"},
    ]
    answers = [
        {"decision": "D1", "value": "awaiting_instructions", "reason": "the meeting is only proposed"},
        {"decision": "D2", "value": "cure_reported", "reason": ""},
    ]
    [result] = score(key, answers, packet)
    assert result.agreed == 1 and result.kappa is None
    assert result.mean_jaccard == pytest.approx((0.5 + 1.0) / 2)
    assert result.specific()["holders_meeting_held"] == 0.0
    assert result.specific()["awaiting_instructions"] == 1.0


def test_date_fields_report_whether_a_date_is_given_as_well_as_exact_agreement():
    key = [
        {"decision": "D1", "field": "notice.period_end", "value": "2026-06-30"},
        {"decision": "D2", "field": "notice.period_end", "value": "none"},
        {"decision": "D3", "field": "notice.period_end", "value": "2026-06-30"},
    ]
    answers = [
        {"decision": "D1", "value": "2026-03-31", "reason": "the certificate's quarter"},
        {"decision": "D2", "value": "None", "reason": ""},
        {"decision": "D3", "value": "2026-06-30", "reason": ""},
    ]
    [result] = score(key, answers, [])
    assert result.kind == "date" and result.agreed == 2 and result.kappa is None
    assert result.presence_agreement == 1.0


def test_unsure_answers_and_hard_cases_are_also_scored_apart():
    key = [
        {"decision": "D1", "field": "breach_item.category", "value": "affirmative", "hard_case": "true"},
        {"decision": "D2", "field": "breach_item.category", "value": "financial", "hard_case": "false"},
    ]
    answers = [
        {"decision": "D1", "value": "financial", "unsure": "true", "reason": "a ratio"},
        {"decision": "D2", "value": "financial", "unsure": "false", "reason": ""},
    ]
    [result] = score(key, answers, [])
    assert result.unsure == 1 and len(result.hard) == 1 and len(result.sure) == 1
    assert result.disagreements[0]["unsure"] == "true"
