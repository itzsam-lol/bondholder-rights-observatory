"""Cross-record integrity, including the rules that keep the source policy enforceable."""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import yaml

from brdo.models import BreachNotice, Claim, Evidence, Instrument, Observation, Provision, SearchRecord
from brdo.store import DatasetError, Severity, check_integrity, load_dataset
from brdo.vocab import (
    CovenantCategory,
    DocumentType,
    ExcerptPolicy,
    InstrumentProperty,
    ProvisionStage,
    RedistributionPolicy,
    RetrievalPolicy,
    SearchChannel,
    SearchOutcome,
    SearchPurpose,
    SourceKind,
)
from tests.conftest import ISIN_LISTED, make_document, make_report, make_row, make_source


def errors(dataset) -> list[str]:
    return [str(p) for p in check_integrity(dataset) if p.severity is Severity.ERROR]


def warnings(dataset) -> list[str]:
    return [str(p) for p in check_integrity(dataset) if p.severity is Severity.WARNING]


def test_the_baseline_fixture_is_clean(dataset):
    assert errors(dataset) == [] and warnings(dataset) == []


def test_evidence_must_cite_a_known_document(dataset):
    claim = Claim(
        property=InstrumentProperty.COUPON_RATE,
        value=10.5,
        asserted_by="trustee-a",
        evidence=[Evidence(document="missing", page=1, quote="abc")],
    )
    dataset.instruments[ISIN_LISTED] = dataset.instruments[ISIN_LISTED].model_copy(update={"claims": [claim]})
    assert any("unknown document missing" in e for e in errors(dataset))


def test_evidence_must_cite_a_document_that_was_hashed(dataset):
    dataset.documents["report-q1"] = make_document(sha256=None)
    assert any("not been retrieved and hashed" in e for e in errors(dataset))


def test_evidence_cannot_point_beyond_the_last_page(dataset):
    dataset.documents["report-q1"] = make_document(pages=1)
    report = make_report(rows=[make_row().model_copy(update={"page": 2})])
    dataset.breach_reports["report-q1"] = report
    assert any("beyond the 1 pages" in e for e in errors(dataset))


def test_quotes_longer_than_the_source_allows_are_refused(dataset):
    dataset.sources["trustee-a"] = make_source(quote_limit=10)
    assert any("whose limit is 10" in e for e in errors(dataset))


def test_a_contract_clause_may_exceed_the_limit_for_other_quotations(dataset):
    dataset.sources["trustee-a"] = make_source(quote_limit=40)
    dataset.provisions["p"] = _provision(text="x" * 200)
    assert not [e for e in errors(dataset) if "whose limit" in e]


def test_quotes_are_refused_from_sources_that_allow_no_excerpts(dataset):
    dataset.sources["trustee-a"] = make_source(excerpts=ExcerptPolicy.NONE)
    assert any("allows no excerpts" in e for e in errors(dataset))


@pytest.mark.parametrize(
    "policy", [dict(retrieval=RetrievalPolicy.EXCLUDED), dict(redistribution=RedistributionPolicy.NO_LINKS)]
)
def test_documents_from_closed_sources_cannot_enter_the_dataset(dataset, policy):
    dataset.sources["trustee-a"] = make_source(**policy)
    assert any("may not be cited by URL" in e for e in errors(dataset))


def test_a_pipeline_retrieval_from_a_manual_only_source_is_an_error(dataset):
    dataset.sources["trustee-a"] = make_source(retrieval=RetrievalPolicy.MANUAL_ONLY)
    when = datetime(2026, 11, 4, tzinfo=UTC)
    dataset.documents["report-q1"] = make_document(retrieved_at=when)
    assert any("does not allow pipeline retrieval" in e for e in errors(dataset))
    dataset.documents["report-q1"] = make_document(retrieved_at=when, retrieved_manually=True)
    assert errors(dataset) == []


@pytest.mark.parametrize("field", ["search", "issuer"])
def test_no_record_may_carry_a_link_to_a_no_links_source(dataset, field):
    dataset.sources["closed"] = make_source(
        "closed", domains=["closed.example"], kind=SourceKind.EXCHANGE, redistribution=RedistributionPolicy.NO_LINKS
    )
    url = "https://archive.closed.example/filing.pdf"
    if field == "search":
        dataset.searches["s"] = SearchRecord(
            id="s",
            performed_on=date(2026, 11, 4),
            subject=ISIN_LISTED,
            purpose=SearchPurpose.CONTRACT_DOCUMENT,
            channel=SearchChannel.WEB_SEARCH,
            outcome=SearchOutcome.LOCATED_NOT_RETRIEVED,
            urls_seen=[url],
        )
    else:
        issuer = dataset.issuers["example-finance"]
        observation = Observation(url=url, observed_on=date(2026, 11, 4), value_seen="x")
        dataset.issuers["example-finance"] = issuer.model_copy(update={"observations": [observation]})
    assert any("whose policy forbids links" in e for e in errors(dataset))


def test_a_superseding_document_must_share_source_and_type(dataset):
    dataset.documents["other"] = make_document("other", type=DocumentType.OTHER)
    dataset.documents["report-q1"] = make_document(supersedes=["other"])
    assert any("different source or document type" in e for e in errors(dataset))


def test_a_trustee_claim_must_name_a_registered_trustee(dataset):
    claim = Claim(
        property=InstrumentProperty.DEBENTURE_TRUSTEE,
        value="nobody",
        asserted_by="trustee-a",
        evidence=[Evidence(document="report-q1", page=1, quote=ISIN_LISTED)],
    )
    dataset.instruments[ISIN_LISTED] = dataset.instruments[ISIN_LISTED].model_copy(update={"claims": [claim]})
    assert any("not a registered debenture trustee" in e for e in errors(dataset))


def test_every_listed_isin_needs_an_instrument_record(dataset):
    del dataset.instruments[ISIN_LISTED]
    assert any("has no instrument record" in e for e in errors(dataset))


def test_a_row_cannot_contradict_the_issuer_of_its_isin(dataset):
    dataset.issuers["other"] = dataset.issuers["example-finance"].model_copy(update={"id": "other"})
    dataset.instruments[ISIN_LISTED] = Instrument(isin=ISIN_LISTED, issuer="other")
    assert any("belongs to other" in e for e in errors(dataset))


def test_isins_with_different_issuer_codes_under_one_issuer_are_flagged(dataset):
    dataset.instruments["INE0N5S07052"] = Instrument(isin="INE0N5S07052", issuer="example-finance")
    assert any("different issuer codes" in w for w in warnings(dataset))


def _provision(**overrides) -> Provision:
    values = dict(
        id="p",
        document="report-q1",
        clause="1",
        page=1,
        text="abc",
        instruments=[ISIN_LISTED],
        category=CovenantCategory.FINANCIAL,
    )
    return Provision(**(values | overrides))


def test_a_provision_may_be_stated_by_a_report_but_not_by_a_circular(dataset):
    dataset.provisions["p"] = _provision()
    assert errors(dataset) == []
    dataset.documents["report-q1"] = make_document(type=DocumentType.REGULATORY_CIRCULAR)
    assert any("cannot state a contractual term" in e for e in errors(dataset))


@pytest.mark.parametrize(
    ("stage", "document_type", "allowed"),
    [
        (ProvisionStage.EXECUTED_TEXT, DocumentType.DEBENTURE_TRUST_DEED, True),
        (ProvisionStage.EXECUTED_TEXT, DocumentType.SUPPLEMENTAL_TRUST_DEED, True),
        (ProvisionStage.EXECUTED_TEXT, DocumentType.KEY_INFORMATION_DOCUMENT, False),
        (ProvisionStage.EXECUTED_TEXT, DocumentType.TRUSTEE_PRESS_RELEASE, False),
        (ProvisionStage.OFFERED, DocumentType.KEY_INFORMATION_DOCUMENT, True),
        (ProvisionStage.OFFERED, DocumentType.PLACEMENT_MEMORANDUM, True),
        (ProvisionStage.OFFERED, DocumentType.DEBENTURE_TRUST_DEED, False),
        (ProvisionStage.OFFERED, DocumentType.EXCHANGE_NOTICE, False),
        (ProvisionStage.PROPOSED, DocumentType.ISSUER_FILING, True),
        (ProvisionStage.APPROVED_IN_PRINCIPLE, DocumentType.EXCHANGE_NOTICE, True),
    ],
)
def test_an_offer_document_is_never_taken_for_the_executed_deed(dataset, stage, document_type, allowed):
    dataset.provisions["p"] = _provision(stage=stage)
    dataset.documents["report-q1"] = make_document(type=document_type)
    stage_errors = [e for e in errors(dataset) if "is marked" in e]
    assert (stage_errors == []) is allowed, stage_errors


def test_an_amendment_must_point_at_an_existing_provision(dataset):
    dataset.provisions["p"] = _provision(amends="ghost")
    assert any("amends unknown provision" in e for e in errors(dataset))


def test_a_notice_must_name_known_instruments(dataset):
    dataset.breach_notices["n"] = BreachNotice(
        id="n", document="report-q1", page=1, trustee="trustee-a", isins=["INE501X07620"], issued_on=date(2026, 8, 1)
    )
    assert any("no instrument record" in e for e in errors(dataset))


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value), encoding="utf-8")


def test_loading_reports_every_invalid_record_with_its_location(tmp_path):
    _write(tmp_path / "sources.yaml", [{"id": "BAD ID", "name": "x"}])
    with pytest.raises(DatasetError) as caught:
        load_dataset(tmp_path)
    assert any("sources.yaml[0]" in str(problem) for problem in caught.value.problems)


def test_an_instrument_file_must_be_named_for_its_isin(tmp_path):
    _write(tmp_path / "instruments" / "INE501X07570.yaml", {"isin": ISIN_LISTED, "issuer": "x"})
    with pytest.raises(DatasetError, match="does not match ISIN"):
        load_dataset(tmp_path)


def test_duplicate_ids_are_refused(tmp_path):
    source = dict(
        id="dup", name="x", kind="other", retrieval="allowed", redistribution="link_only", excerpts="short_quotation"
    )
    _write(tmp_path / "sources.yaml", [source, source])
    with pytest.raises(DatasetError, match="duplicate id"):
        load_dataset(tmp_path)


def test_an_empty_data_directory_loads_as_an_empty_dataset(tmp_path):
    assert load_dataset(tmp_path).instruments == {}


def test_a_file_that_is_not_valid_yaml_is_reported_as_a_dataset_error(tmp_path):
    (tmp_path / "sources.yaml").write_text("- id: x\n  name: [unclosed\n", encoding="utf-8")
    with pytest.raises(DatasetError, match="sources.yaml: is not valid YAML"):
        load_dataset(tmp_path)
