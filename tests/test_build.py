import csv
import sqlite3

from brdo.build import tables, write_csv, write_sqlite
from brdo.report import linkage_funnel, render_report
from brdo.vocab import AiTrainingSignal
from tests.conftest import ISIN_LISTED, make_source


def test_breach_items_are_exported_in_long_form_with_printed_and_parsed_dates(dataset):
    row = tables(dataset)["breach_report_items"][0]
    assert row["isin"] == ISIN_LISTED
    assert row["actual_breach_as_reported"] == "30-06-26"
    assert row["actual_breach"] == "2026-06-30"
    assert row["specificity"] == "clause_text"


def test_every_output_format_carries_the_same_rows(dataset, tmp_path):
    all_tables = tables(dataset)
    write_csv(all_tables, tmp_path)
    database = write_sqlite(all_tables, tmp_path / "out.sqlite")
    with (tmp_path / "instrument_status.csv").open(encoding="utf-8") as handle:
        from_csv = list(csv.DictReader(handle))
    with sqlite3.connect(database) as connection:
        count = connection.execute("SELECT COUNT(*) FROM instrument_status").fetchone()[0]
    assert count == len(from_csv) == len(all_tables["instrument_status"])


def test_exports_are_deterministic(dataset, tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    write_csv(tables(dataset), first)
    write_csv(tables(dataset), second)
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes()


def test_rows_from_sources_reserving_ai_training_are_flagged(dataset):
    assert tables(dataset)["breach_report_items"][0]["ai_training_reserved"] == "false"
    dataset.sources["trustee-a"] = make_source(ai_training=AiTrainingSignal.RESERVED)
    exported = tables(dataset)
    assert exported["breach_report_items"][0]["ai_training_reserved"] == "true"
    assert {row["ai_training_reserved"] for row in exported["evidence"]} == {"true"}


def test_the_report_carries_its_disclaimer_and_never_speaks_of_compliance_as_a_finding(dataset):
    text = render_report(dataset)
    assert "not findings about whether any issuer or trustee complied" in text
    assert "absence of a reported breach is not evidence that none occurred" in text


def test_the_funnel_counts_only_what_the_records_support(dataset):
    stages = dict(linkage_funnel(dataset))
    assert stages["listed in a reviewed trustee breach report"] == 1
    assert stages["the contract itself retrieved, hashed and linked"] == 0
