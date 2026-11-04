"""Shared builders for small, synthetic datasets. Nothing here stands for a real issuer."""

from datetime import date
from pathlib import Path

import pytest
from pypdf import PageObject, PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject

from brdo.models import (
    BreachItem,
    BreachReport,
    BreachRow,
    Claim,
    ComplianceStatement,
    Document,
    Evidence,
    Instrument,
    Issuer,
    Period,
    ReportedDate,
    Source,
    StatedException,
)
from brdo.store import Dataset
from brdo.vocab import (
    CovenantCategory,
    CovenantSpecificity,
    DocumentType,
    ExcerptPolicy,
    InstrumentProperty,
    RedistributionPolicy,
    RetrievalPolicy,
    SourceKind,
    StatementMaker,
    StatementScope,
)

ISIN_LISTED = "INE501X07588"
ISIN_UNLISTED = "INE501X07570"
QUARTER = Period(start=date(2026, 4, 1), end=date(2026, 6, 30))
SHA = "a" * 64


def make_source(identifier: str = "trustee-a", **overrides) -> Source:
    values = dict(
        id=identifier,
        name=identifier.title(),
        kind=SourceKind.DEBENTURE_TRUSTEE,
        domains=[f"{identifier}.example"],
        retrieval=RetrievalPolicy.ALLOWED,
        redistribution=RedistributionPolicy.LINK_ONLY,
        excerpts=ExcerptPolicy.SHORT_QUOTATION,
    )
    return Source(**(values | overrides))


def make_document(identifier: str = "report-q1", source: str = "trustee-a", **overrides) -> Document:
    values = dict(
        id=identifier,
        source=source,
        type=DocumentType.TRUSTEE_BREACH_STATUS_REPORT,
        title=identifier,
        url=f"https://{source}.example/{identifier}.pdf",
        sha256=SHA,
        media_type="application/pdf",
        pages=3,
        period=QUARTER,
    )
    return Document(**(values | overrides))


def make_row(isin: str = ISIN_LISTED, *, uncertain: bool = False, carried: date | None = None) -> BreachRow:
    return BreachRow(
        row="1",
        page=1,
        issuer_name_as_reported="Example Finance Limited",
        issuer="example-finance",
        items=[
            BreachItem(
                isins=[isin],
                covenant_as_reported="maintain a ratio of less than 5%",
                levels_stated=["5%"],
                page=1,
                category=CovenantCategory.FINANCIAL,
                specificity=CovenantSpecificity.CLAUSE_TEXT,
                assignment_uncertain=uncertain,
            )
        ],
        actual_breach=ReportedDate(raw="30-06-26", value=date(2026, 6, 30)),
        detected=ReportedDate(raw="14-08-26", value=date(2026, 8, 14)),
        carried_over_from=carried,
    )


def make_report(document: str = "report-q1", rows: list[BreachRow] | None = None, **overrides) -> BreachReport:
    values = dict(
        document=document,
        trustee="trustee-a",
        period=QUARTER,
        extraction_complete=True,
        visually_reviewed=True,
        rows=[make_row()] if rows is None else rows,
    )
    return BreachReport(**(values | overrides))


def trustee_claim(trustee: str = "trustee-a", document: str = "report-q1") -> Claim:
    return Claim(
        property=InstrumentProperty.DEBENTURE_TRUSTEE,
        value=trustee,
        asserted_by=trustee,
        evidence=[Evidence(document=document, page=1, quote=ISIN_LISTED)],
    )


@pytest.fixture
def dataset(tmp_path: Path) -> Dataset:
    """One trustee, one complete report listing one of the issuer's two instruments."""
    return Dataset(
        root=tmp_path,
        sources={"trustee-a": make_source()},
        documents={"report-q1": make_document()},
        issuers={"example-finance": Issuer(id="example-finance", name="Example Finance Limited")},
        instruments={
            ISIN_LISTED: Instrument(isin=ISIN_LISTED, issuer="example-finance", claims=[trustee_claim()]),
            ISIN_UNLISTED: Instrument(isin=ISIN_UNLISTED, issuer="example-finance", claims=[trustee_claim()]),
        },
        breach_reports={"report-q1": make_report()},
    )


def write_pdf(path: Path, pages: list[bytes]) -> Path:
    """Write a PDF whose pages run the given content streams, with Helvetica available as /F1."""
    writer = PdfWriter()
    for content in pages:
        page = PageObject.create_blank_page(width=612, height=792)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
        )
        stream = DecodedStreamObject()
        stream.set_data(content)
        page[NameObject("/Contents")] = writer._add_object(stream)
        page[NameObject("/MediaBox")] = ArrayObject([NumberObject(n) for n in (0, 0, 612, 792)])
        writer.add_page(page)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def text_stream(text: str) -> bytes:
    escaped = text.replace("(", r"\(").replace(")", r"\)")
    return f"BT /F1 10 Tf 40 700 Td ({escaped}) Tj ET".encode("latin-1")


def make_statement(
    identifier: str = "statement-q1",
    *,
    breach: bool,
    isin: str = ISIN_LISTED,
    scope: StatementScope = StatementScope.ALL_COVENANTS,
    made_by: StatementMaker = StatementMaker.ISSUER,
    exceptions: list[StatedException] | None = None,
) -> ComplianceStatement:
    return ComplianceStatement(
        id=identifier,
        document="report-q1",
        instruments=[isin],
        period=QUARTER,
        stated_by="trustee-a",
        made_by=made_by,
        scope=scope,
        breach_stated=breach,
        exceptions=exceptions or [],
        evidence=[Evidence(document="report-q1", page=1, quote="complied")],
    )
