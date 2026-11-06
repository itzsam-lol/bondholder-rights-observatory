"""Label-blind second-annotation materials, agreement scoring, and the rules that keep a review honest."""

import re
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from brdo.models import AnnotationReview, BreachItem, Provision
from brdo.pit import as_of
from brdo.review import (
    ANSWER_COLUMNS,
    FIELD_KINDS,
    KEY_COLUMNS,
    PACKET_COLUMNS,
    PROBLEMS,
    AnswersUnreadable,
    PacketRefused,
    answer_error,
    canonical,
    cohen_kappa,
    decisions,
    normalise_answer,
    read_answers,
    read_csv,
    render_scores,
    review_problems,
    round_fields,
    score,
    submission_errors,
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


def test_a_packet_carries_the_reviewers_guide_and_a_table_of_its_fields(dataset, tmp_path):
    guide = tmp_path / "guide.md"
    guide.write_text("# Guide\n", encoding="utf-8")
    written = write_packet(dataset, tmp_path / "round", _codebook(tmp_path), "abcdef0", guide=guide)
    assert (written["packet"] / "guide.md").read_text(encoding="utf-8") == "# Guide\n"
    readme = (written["packet"] / "README.txt").read_text(encoding="utf-8")
    assert "breach_item.category: 1 decisions, categorical" in readme and "hash_mismatch" in readme
    assert list(read_csv(written["packet"] / "answers.csv")[0]) == ANSWER_COLUMNS
    assert not (written["packet"] / "key.csv").exists()


def test_the_reviewers_guide_explains_every_field_and_problem_code():
    guide = (REPOSITORY / "docs" / "reviewer-guide.md").read_text(encoding="utf-8")
    assert [field for field in FIELD_KINDS if f"`{field}`" not in guide] == []
    assert all(f"`{problem}`" in guide for problem in PROBLEMS)
    for words in ("SHA-256", "shasum -a 256", "sha256sum", "Get-FileHash", "`none`", "unsure", "answers.csv"):
        assert words in guide, words


def test_reported_problems_are_counted_apart_and_a_blank_value_stays_unanswered():
    key = [
        {"decision": "D1", "decision_id": "a:category", "field": "breach_item.category", "value": "financial"},
        {"decision": "D2", "decision_id": "b:category", "field": "breach_item.category", "value": "other"},
    ]
    answers = [
        {"decision": "D1", "value": "", "unsure": "", "reason": "the site refuses", "problem": "source_unavailable"},
        {
            "decision": "D2",
            "value": "other",
            "unsure": "true",
            "reason": "partly illegible",
            "problem": "cannot_interpret",
        },
    ]
    [result] = score(key, answers, [])
    assert result.answered == 1 and result.agreed == 1
    assert result.problems == {"source_unavailable": 1, "cannot_interpret": 1}
    rendered = render_scores([result])
    assert "| a:category | source_unavailable | the site refuses |" in rendered


def _category_key(*values: str, hard: str = "false") -> list[dict[str, str]]:
    return [
        {
            "decision": f"D{i}",
            "decision_id": f"r{i}:category",
            "field": "breach_item.category",
            "value": value,
            "hard_case": hard,
        }
        for i, value in enumerate(values, start=1)
    ]


_CATEGORY_LINE = {"kind": "categorical", "multiple": "false", "allowed": "financial|affirmative|negative|other"}
DATE = "a date as YYYY-MM-DD, or none"


def _packet_for(key: list[dict[str, str]], line: dict[str, str] | None = None) -> list[dict[str, str]]:
    return [dict(line or _CATEGORY_LINE, decision=row["decision"], field=row["field"]) for row in key]


def _one(
    value: str, problem: str = "", unsure: str = "false", line: dict[str, str] | None = None, key_value="financial"
):
    key = _category_key(key_value)
    answers = [
        {
            "decision": "D1",
            "field": "breach_item.category",
            "value": value,
            "unsure": unsure,
            "reason": "r",
            "problem": problem,
        }
    ]
    [result] = score(key, answers, _packet_for(key, line))
    assert result.accounted
    return result


def _category(result) -> str:
    if result.answered:
        return "answered"
    if result.blank:
        return "blank"
    if result.excluded:
        return "excluded"
    if result.invalid:
        return "not scorable"
    return "missing"


@pytest.mark.parametrize(
    ("value", "problem", "unsure", "expected", "warned"),
    [
        ("financial", "", "false", "answered", False),
        ("Financial", "", "FALSE", "answered", False),
        ("financial", "cannot_interpret", "true", "answered", False),
        ("financial", "cannot_interpret", "false", "answered", True),
        ("financial", "cannot_interpret", "", "answered", True),
        ("financial", " Cannot_Interpret ", "true", "answered", False),
        ("", "cannot_interpret", "", "excluded", False),
        ("financial", "source_unavailable", "false", "excluded", False),
        ("financial", "hash_mismatch", "false", "excluded", False),
        ("financial", "page_not_found", "false", "excluded", False),
        ("", "source_unavailable", "", "excluded", False),
        ("financial", "illegible", "false", "not scorable", False),
        ("financial", "source unavailable", "false", "not scorable", False),
        ("financial", "hash-mismatch", "false", "not scorable", False),
        ("financial", "source_unavailable|cannot_interpret", "false", "not scorable", False),
        ("financial", "hash_mismatch, source_unavailable", "false", "not scorable", False),
        ("", "illegible", "", "not scorable", False),
        ("finance", "cannot_interpret", "true", "not scorable", False),
        ("finance", "", "false", "not scorable", False),
        ("financial|other", "", "false", "not scorable", False),
        ("", "", "", "blank", False),
        ("  ", "", "", "blank", False),
        ("financial", "", "maybe", "answered", True),
    ],
)
def test_each_response_falls_in_exactly_one_category(value, problem, unsure, expected, warned):
    result = _one(value, problem, unsure)
    assert _category(result) == expected
    assert bool(result.warnings) is warned
    assert bool(result.pairs) is (expected == "answered")


def test_no_combined_misspelt_or_unknown_code_lets_a_value_into_agreement():
    for code in (
        "source_unavailable|cannot_interpret",
        "cannot_interpret;source_unavailable",
        "Source Unavailable",
        "hash-mismatch",
        "page not found",
        "cannot interpret",
        "none",
        "n/a",
    ):
        result = _one("financial", code)
        assert result.pairs == [] and result.unrecognised == {code.strip().lower(): 1}, code
        assert "unrecognised problem code" in result.invalid[0]["why"]


def test_cannot_interpret_with_a_value_not_marked_unsure_is_a_conspicuous_warning():
    result = _one("other", "cannot_interpret", "false")
    assert result.answered == 1 and result.disagreements
    rendered = render_scores([result])
    assert "**Warnings: 1 lines to raise with the reviewer" in rendered
    assert rendered.index("**Warnings") < rendered.index("| field | kind |")
    assert "cannot_interpret with a value, but unsure is not true" in rendered


def test_none_is_a_value_alone_and_not_with_other_labels():
    line = {"kind": "multi_label", "multiple": "true", "allowed": "awaiting_instructions|cure_reported|none"}
    assert _category(_one("none", line=line, key_value="none")) == "answered"
    assert _one("none", line=line, key_value="none").agreed == 1
    assert _category(_one("none|cure_reported", line=line, key_value="none")) == "not scorable"
    assert _category(_one("cure_reported||none", line=line, key_value="none")) == "not scorable"
    assert answer_error("none", "multi_label", "cure_reported|none", True) is None


def test_dates_must_be_real_and_written_as_iso_dates():
    assert answer_error("2026-06-30", "date", DATE, False) is None
    assert answer_error("None", "date", DATE, False) is None
    assert answer_error("30/06/2026", "date", DATE, False)
    assert answer_error("2026-02-30", "date", DATE, False)


def test_blank_and_excluded_are_shown_apart_and_problem_codes_are_counted_by_field():
    key = _category_key("financial", "other", "financial", "financial")
    answers = [
        {
            "decision": "D1",
            "field": "breach_item.category",
            "value": "",
            "problem": "source_unavailable",
            "reason": "refused",
        },
        {
            "decision": "D2",
            "field": "breach_item.category",
            "value": "",
            "problem": "cannot_interpret",
            "reason": "illegible",
        },
        {"decision": "D3", "field": "breach_item.category", "value": "", "problem": "", "reason": ""},
        {
            "decision": "D4",
            "field": "breach_item.category",
            "value": "financial",
            "problem": "illegible",
            "reason": "faint",
        },
    ]
    [result] = score(key, answers, _packet_for(key))
    assert (result.blank, len(result.excluded), len(result.invalid), result.answered) == (1, 2, 1, 0)
    assert result.problems == {"source_unavailable": 1, "cannot_interpret": 1} and result.unrecognised == {
        "illegible": 1
    }
    rendered = render_scores([result])
    assert "| breach_item.category | categorical | 4 | 0 | 1 | 2 | 1 | 0 |" in rendered
    assert "| field | source_unavailable | cannot_interpret | unrecognised |" in rendered
    assert "| breach_item.category | 1 | 1 | 1 |" in rendered


def test_a_duplicated_decision_is_never_resolved_by_choosing_a_line():
    key = _category_key("financial", "other")
    same = {"decision": "D1", "field": "breach_item.category", "value": "financial", "unsure": "false"}
    for second in (same, dict(same, value="other")):
        answers = [same, dict(second), {"decision": "D2", "field": "breach_item.category", "value": "other"}]
        [result] = score(key, answers, _packet_for(key))
        assert result.accounted and result.answered == 1 and "no line is chosen" in result.invalid[0]["why"]
        assert any("appear on more than one line" in e for e in submission_errors(key, answers, _packet_for(key)))


def test_an_unstated_unsure_is_neither_sure_nor_unsure_and_missing_reasons_are_counted():
    key = _category_key("financial", "financial", hard="true")
    answers = [
        {"decision": "D1", "field": "breach_item.category", "value": "financial", "unsure": "", "reason": ""},
        {"decision": "D2", "field": "breach_item.category", "value": "financial", "unsure": "false", "reason": "ok"},
    ]
    [result] = score(key, answers, [])
    assert (result.unsure, result.unsure_unstated, len(result.sure), result.reasons_missing) == (0, 1, 1, 1)


def test_kappa_is_withheld_not_annotated_when_pairs_are_few_or_one_value_dominates():
    def answered(values, seconds):
        key = _category_key(*values)
        answers = [
            {"decision": k["decision"], "value": v, "unsure": "false"} for k, v in zip(key, seconds, strict=False)
        ]
        [result] = score(key, answers, [])
        return result

    few = answered(["financial", "other"] * 3, ["financial", "other", "financial", "other", "other", "other"])
    assert few.kappa is not None and few.reported_kappa is None
    assert few.kappa_withheld() == "only 6 answered pairs, fewer than 20"
    rendered = render_scores([few])
    assert "| not reported: only 6 answered pairs, fewer than 20 |" in rendered
    assert f"{few.kappa:.2f}" not in rendered.split("| field |")[1].split("Kappa is computed")[0]
    assert "- original → second: financial → financial 2, financial → other 1, other → other 3" in rendered
    assert "- answered pairs: 6; agreed: 5; raw agreement: 0.83" in rendered

    skewed = answered(["financial"] * 19 + ["other"], ["financial"] * 20)
    assert skewed.reported_kappa is None and "financial is 19 of 20 original values" in skewed.kappa_withheld()

    stable = answered(["financial", "other"] * 10, ["financial", "other"] * 9 + ["other", "other"])
    assert stable.reported_kappa == pytest.approx(stable.kappa) and stable.kappa_withheld() is None
    assert f"| {stable.kappa:.2f} |" in render_scores([stable])


def test_multi_label_scores_show_counts_for_each_label_and_say_what_exact_set_agreement_misses():
    key = [
        {"decision": "D1", "field": "breach_row.actions", "value": "awaiting_instructions|holders_meeting_held"},
        {"decision": "D2", "field": "breach_row.actions", "value": "none"},
    ]
    packet = [
        {
            "decision": row["decision"],
            "multiple": "true",
            "kind": "multi_label",
            "allowed": "awaiting_instructions|holders_meeting_held|cure_reported|none",
        }
        for row in key
    ]
    answers = [
        {"decision": "D1", "value": "awaiting_instructions|cure_reported", "unsure": "false"},
        {"decision": "D2", "value": "NONE", "unsure": "false"},
    ]
    [result] = score(key, answers, packet)
    assert result.agreed == 1
    assert result.label_counts() == {
        "awaiting_instructions": (1, 0, 0),
        "cure_reported": (0, 0, 1),
        "holders_meeting_held": (0, 1, 0),
    }
    rendered = render_scores([result])
    assert "exact agreement on the whole set" in rendered and "partial agreement" in rendered
    assert "holders_meeting_held 0.00 (both 0, original only 1, second only 0)" in rendered
    assert "not an estimate of reliability for annotations outside the packet" in rendered


def _round_one(dataset):
    chosen = [d for d in decisions(dataset) if round_fields(dataset, "1")(d)]
    ids = [f"D{i:04d}" for i in range(1, len(chosen) + 1)]
    packet = [{k: str(v) for k, v in d.packet_row(i).items()} for i, d in zip(ids, chosen, strict=True)]
    key = [
        {
            "decision": i,
            "decision_id": d.id,
            "record": d.record,
            "field": d.field,
            "value": d.value,
            "hard_case": "true" if d.hard_case_note else "false",
        }
        for i, d in zip(ids, chosen, strict=True)
    ]
    return key, packet


@pytest.fixture(scope="module")
def release():
    from brdo.store import load_dataset

    return load_dataset(REPOSITORY / "data")


def test_a_wholly_blank_submission_is_valid_unanswered_and_reports_no_agreement(release):
    key, packet = _round_one(release)
    blank = [dict.fromkeys(ANSWER_COLUMNS, "") | {"decision": k["decision"], "field": k["field"]} for k in key]
    assert submission_errors(key, blank, packet, ANSWER_COLUMNS) == []
    results = score(key, blank, packet)
    assert all(r.accounted and r.blank == r.decisions and not r.pairs for r in results)
    rendered = render_scores(results)
    assert rendered.startswith(f"**No answers were supplied.** Of {len(key)} decisions, {len(key)} are blank")
    assert "**breach_item.category**" not in rendered


def test_structural_faults_are_errors(release):
    key, packet = _round_one(release)
    good = [dict.fromkeys(ANSWER_COLUMNS, "") | {"decision": k["decision"], "field": k["field"]} for k in key]
    assert submission_errors(key, good, packet, ANSWER_COLUMNS) == []
    cases = {
        "no header line": (key, [], packet, []),
        "header but no lines": (key, [], packet, ANSWER_COLUMNS),
        "no column value": (
            key,
            [{c: v for c, v in r.items() if c != "value"} for r in good],
            packet,
            [c for c in ANSWER_COLUMNS if c != "value"],
        ),
        "more than one line": (key, good + [good[0]], packet, ANSWER_COLUMNS),
        "not in the key": (key, good + [dict(good[0], decision="D9999")], packet, ANSWER_COLUMNS),
        "no decision id": (key, good + [dict(good[0], decision=" ")], packet, ANSWER_COLUMNS),
        "a field other than the key's": (key, [dict(good[0], field="notice.kind"), *good[1:]], packet, ANSWER_COLUMNS),
        "more cells than the header": (key, [{**good[0], None: ["x"]}, *good[1:]], packet, ANSWER_COLUMNS),
        "packet does not match the key": (key, good, packet[:-1], ANSWER_COLUMNS),
    }
    for expected, arguments in cases.items():
        errors = submission_errors(*arguments)
        assert any(expected in e for e in errors), (expected, errors)


def test_a_packet_from_another_round_is_detected(release):
    key, _ = _round_one(release)
    chosen = [d for d in decisions(release) if round_fields(release, "2")(d)]
    other = [{k: str(v) for k, v in d.packet_row(f"D{i:04d}").items()} for i, d in enumerate(chosen, start=1)]
    answers = [dict.fromkeys(ANSWER_COLUMNS, "") | {"decision": k["decision"], "field": k["field"]} for k in key]
    assert any("packet does not match the key" in e for e in submission_errors(key, answers, other, ANSWER_COLUMNS))


def test_answers_files_are_read_strictly_as_utf8_csv(tmp_path):
    good = tmp_path / "good.csv"
    good.write_text(
        "\ufeffdecision,field,value,unsure,reason,problem\r\n D1 ,breach_item.category, Financial ,FALSE,,\r\n", "utf-8"
    )
    columns, rows = read_answers(good)
    assert columns == ANSWER_COLUMNS and rows[0]["value"] == " Financial "
    [result] = score(_category_key("financial"), rows, [])
    assert (result.answered, result.agreed) == (1, 1)
    latin = tmp_path / "latin.csv"
    latin.write_bytes("decision,field,value,unsure,reason,problem\nD1,f,financial,false,déjà vu,\n".encode("cp1252"))
    with pytest.raises(AnswersUnreadable, match="not UTF-8"):
        read_answers(latin)
    with pytest.raises(AnswersUnreadable, match="does not exist"):
        read_answers(tmp_path / "absent.csv")
    empty = tmp_path / "empty.csv"
    empty.write_text("", "utf-8")
    assert read_answers(empty) == ([], [])


def test_the_score_command_fails_loudly_and_prints_no_table_for_a_faulty_file(dataset, tmp_path, capsys):
    from brdo.cli import main

    written = write_packet(dataset, tmp_path / "round", _codebook(tmp_path), "abcdef0")
    arguments = [
        "review",
        "score",
        "--decisions",
        str(written["packet"] / "decisions.csv"),
        "--key",
        str(written["key"] / "key.csv"),
    ]
    blank = written["packet"] / "answers.csv"
    assert main([*arguments, "--answers", str(blank)]) == 0
    assert "No answers were supplied" in capsys.readouterr().out
    faulty = tmp_path / "faulty.csv"
    faulty.write_text("decision;field;value;unsure;reason;problem\nD0001;x;;;;\n", "utf-8")
    assert main([*arguments, "--answers", str(faulty)]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and "no scores are reported" in captured.err
    latin = tmp_path / "latin.csv"
    latin.write_bytes(blank.read_bytes() + "D9,x,é,,,\n".encode("cp1252"))
    assert main([*arguments, "--answers", str(latin)]) == 1
    assert "not UTF-8" in capsys.readouterr().err


def test_a_packet_round_trips_through_the_scorer_without_any_answer_counting_as_negative(dataset, tmp_path):
    written = write_packet(dataset, tmp_path / "round", _codebook(tmp_path), "abcdef0")
    key = read_csv(written["key"] / "key.csv")
    packet = read_csv(written["packet"] / "decisions.csv")
    columns, blank = read_answers(written["packet"] / "answers.csv")
    assert len(blank) == len(key) == len(packet)
    assert all(not row["value"] and not row["unsure"] and not row["problem"] for row in blank)
    assert submission_errors(key, blank, packet, columns) == []
    results = score(key, blank, packet)
    assert all(r.accounted and r.answered == 0 and r.blank == r.decisions for r in results)


def test_no_letter_decision_carries_a_passage(release):
    letters = [d for d in decisions(release) if d.field.startswith("notice.")]
    assert len(letters) == 198 and {d.passage for d in letters} == {""}
    assert all(d.page and d.locator.startswith("letter dated ") and d.isins for d in letters)


def test_whether_a_line_has_a_passage_never_varies_within_a_field_except_with_the_source_cell(release):
    """Passage presence must not be a signal of the value. Only fields whose passage is the transcription of the very
    cell being judged may have a passage, and those always have one."""
    by_field: dict[str, set[bool]] = {}
    for decision in decisions(release):
        by_field.setdefault(decision.field, set()).add(bool(decision.passage))
    assert all(len(presence) == 1 for presence in by_field.values()), by_field
    with_passage = {field for field, presence in by_field.items() if presence == {True}}
    assert with_passage <= {
        "breach_item.category",
        "breach_item.specificity",
        "breach_item.assignment_uncertain",
        "breach_row.actions",
        "provision.category",
        "provision.stage",
        "provision_link.agreement",
    }


def test_letter_lines_have_no_column_that_varies_with_curation(release):
    """Every column of a letter line that the curator's work could shape is the same for all 66 letters of each field.

    The page, the letter's date (in the locator), the document and the ISINs vary, because they locate the letter in
    its source. They are kept, although the order they show is associated with the values (docs/reliability.md).
    """
    key, packet = _round_one(release)
    rows = [(k, p) for k, p in zip(key, packet, strict=True) if k["field"].startswith("notice.")]
    assert len(rows) == 198
    for field in {k["field"] for k, _ in rows}:
        lines = [p for k, p in rows if k["field"] == field]
        for column in ("passage", "hard_case", "hard_case_note", "rule", "allowed", "kind", "multiple"):
            assert len({p[column] for p in lines}) == 1, (field, column)
        assert all(p["locator"].startswith("letter dated ") and p["page"] and p["isins"] for p in lines)


def test_statement_lines_give_pages_and_isins_but_not_the_records_own_quotations(release):
    lines = [d for d in decisions(release) if d.field.startswith("statement.")]
    assert lines and all(d.passage == "" and d.page is not None and d.isins for d in lines)
    quotes = {item.quote for statement in release.compliance_statements.values() for item in statement.evidence}
    assert not [d for d in lines if any(q and q in d.locator for q in quotes)]
    made_by = [d for d in lines if d.field == "statement.made_by"]
    where = [(d.document, d.page, d.locator, d.isins) for d in made_by]
    assert len(set(where)) == len(where)
    assert "pages 4, 8" in next(d.locator for d in made_by if d.record == "dvara-2026-06-exceptions")


def test_an_answer_line_without_its_field_is_a_structural_error(release):
    key, packet = _round_one(release)
    answers = [dict.fromkeys(ANSWER_COLUMNS, "") | {"decision": k["decision"], "field": k["field"]} for k in key]
    answers[0]["field"] = " "
    assert any("have no field" in e for e in submission_errors(key, answers, packet, ANSWER_COLUMNS))


@pytest.mark.parametrize(
    "content",
    [
        'decision,field,value,unsure,reason,problem\nD1,breach_item.category,"financial,false,,\n',
        'decision,field,value,unsure,reason,problem\nD1,breach_item.category,"fin"ancial,false,,\n',
    ],
)
def test_malformed_csv_is_a_controlled_error(tmp_path, content):
    path = tmp_path / "answers.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(AnswersUnreadable, match="not readable as CSV"):
        read_answers(path)


def test_an_unreadable_key_or_packet_exits_2_without_a_traceback(dataset, tmp_path, capsys):
    from brdo.cli import main

    written = write_packet(dataset, tmp_path / "round", _codebook(tmp_path), "abcdef0")
    decisions_csv, key_csv = written["packet"] / "decisions.csv", written["key"] / "key.csv"
    answers = written["packet"] / "answers.csv"
    broken = tmp_path / "broken.csv"
    broken.write_text("decision,record\nD0001,x\n", encoding="utf-8")
    quoted = tmp_path / "quoted.csv"
    quoted.write_text('decision,field,kind,allowed,multiple\nD0001,"x,y,z,w\n', encoding="utf-8")
    for key, packet, words in (
        (broken, decisions_csv, "has no column"),
        (key_csv, quoted, "cannot be read as UTF-8 CSV"),
        (tmp_path / "absent.csv", decisions_csv, "does not exist"),
    ):
        status = main(["review", "score", "--decisions", str(packet), "--key", str(key), "--answers", str(answers)])
        captured = capsys.readouterr()
        assert status == 2 and captured.out == "" and words in captured.err
