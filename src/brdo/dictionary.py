"""What every exported column means, what kind of statement it is, and where its facts originate.

A reader of a flat file cannot otherwise tell a quotation from a parsed fact, a fact from the project's
classification, or the party that published a fact from the party it came from. This module is the single source of
those descriptions. ``datapackage`` turns them into a Frictionless Data Package descriptor for ``exports/``, and
``render_markdown`` into ``docs/data-dictionary.md``. Tests fail if an exported column is undocumented.
"""

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

REPOSITORY_URL = "https://github.com/itzsam-lol/bondholder-rights-observatory"


class ColumnKind(StrEnum):
    """What kind of statement a column holds. Every column has exactly one kind."""

    IDENTIFIER = "identifier"
    """A key: an ISIN, or the id of a record in this dataset."""
    SOURCE_TEXT = "source_text"
    """Verbatim text from a source document. It belongs to its owner, is not covered by the dataset's licence, and is
    kept short under the source's quotation limit."""
    READ_FROM_SOURCE = "read_from_source"
    """A fact read from a source, such as a printed date parsed into ISO form, an ISIN, a level or a party. The source
    said it; the project transcribed it."""
    ANNOTATION = "annotation"
    """The project's classification or interpretation, made by one curator and not yet independently reviewed."""
    DERIVED = "derived"
    """Computed mechanically by code in this repository from other fields. It can be recomputed and challenged."""
    PROVENANCE = "provenance"
    """About where, when and how the project obtained something, or under what policy it may be used."""


KIND_GUIDE = {
    ColumnKind.IDENTIFIER: "A key: an ISIN or the id of a record in this dataset.",
    ColumnKind.SOURCE_TEXT: (
        "Verbatim text from a source. Not covered by the dataset's licence, and cut to the source's quotation limit."
    ),
    ColumnKind.READ_FROM_SOURCE: "A fact the source states, transcribed or parsed by the project.",
    ColumnKind.ANNOTATION: "The project's classification or reading. Single-pass; not yet independently reviewed.",
    ColumnKind.DERIVED: "Computed by code in this repository from other fields.",
    ColumnKind.PROVENANCE: "Where, when and how something was obtained, or the policy governing its use.",
}


@dataclass(frozen=True)
class Column:
    kind: ColumnKind
    description: str
    origin: str | None = None
    """Where the fact originates, when that is not simply the party that published the document."""
    type: str | None = None
    """Frictionless type, when inference from the values could mislead."""
    empty: str | None = None
    """What an empty cell means, where that matters: unknown, not applicable, not recorded or not yet established."""
    licensed: bool | None = None
    """Whether the project's licence covers the column. By default, every kind but ``source_text`` is covered."""
    rights: str | None = None
    """What a reuser must know about third-party text in the column."""

    @property
    def is_licensed(self) -> bool:
        return self.licensed if self.licensed is not None else self.kind is not ColumnKind.SOURCE_TEXT


@dataclass(frozen=True)
class Table:
    description: str
    columns: dict[str, Column]


K = ColumnKind

ISIN = Column(K.IDENTIFIER, "ISIN of the instrument, validated by its check digit.", type="string")
DOCUMENT = Column(K.IDENTIFIER, "Id of the cited file in `documents.csv`.")
PAGE = Column(K.PROVENANCE, "1-based page of the file, not the printed page number, on which the item is printed.")
AI_RESERVED = Column(
    K.PROVENANCE,
    "True when the row derives from a source that publishes a reservation against AI training. Exclude such rows from "
    "any training or benchmark use.",
)
TRUSTEE = Column(K.IDENTIFIER, "Id of the debenture trustee in `sources.csv`.")
REPORT = Column(K.IDENTIFIER, "Id of the trustee's breach report, a document in `documents.csv`.")
STATEMENT = Column(K.IDENTIFIER, "Id of the compliance statement in `compliance_statements.csv`.")
PERIOD_END = Column(K.READ_FROM_SOURCE, "Last day of the reporting period the document states it covers.")
PERIOD_START = Column(K.READ_FROM_SOURCE, "First day of the reporting period the document states it covers.")
EVIDENCE = Column(
    K.PROVENANCE, "The anchors supporting the record, as `document#pPAGE`, separated by `; `. See `evidence.csv`."
)
OBSERVED_AT = Column(
    K.PROVENANCE,
    "Pages of sources whose terms forbid storing their content, such as depository databases, where the value was "
    "seen. The page's content is not stored and cannot be re-verified by machine.",
)
PROJECT_TEXT = "The project's text, under CC BY 4.0. Words it quotes from a source remain their owner's."
TRADE_NAME = (
    "A name of an entity, as a source prints it. Trade names are not licensed by the project (LICENSE-DATA.md)."
)
FLOW_RIGHTS = "The pointers are the project's; each `matched` text is a short quotation from the source, not licensed."
NOTE = Column(K.ANNOTATION, "The project's remark.", rights=PROJECT_TEXT)
TRUSTEE_ORIGIN_DATES = (
    "Published by the trustee. Two trustees define the date of actual breach by the issuer's or auditor's certificate "
    "(see their printed notes in the observability report), so for them it originates with the issuer."
)


TABLES: dict[str, Table] = {
    "sources": Table(
        "One row per publisher, with the project's access and reuse policy for it. See docs/source-policy.md.",
        {
            "id": Column(K.IDENTIFIER, "Id of the source."),
            "name": Column(K.READ_FROM_SOURCE, "The publisher's name.", licensed=False, rights=TRADE_NAME),
            "kind": Column(
                K.ANNOTATION, "What kind of publisher it is: regulator, exchange, trustee, issuer and so on."
            ),
            "retrieval": Column(
                K.PROVENANCE,
                "Whether the project's pipeline may retrieve from it: `allowed`, `manual_only` (a person downloads in "
                "a browser and the file is ingested by hash) or `excluded` (not used, not even linked).",
            ),
            "redistribution": Column(
                K.PROVENANCE,
                "What the project publishes about the source's documents: `link_only` (links, hashes, short "
                "quotations) or `no_links` (not even a link).",
            ),
            "excerpts": Column(K.PROVENANCE, "Whether any quotation is published from the source."),
            "quote_limit": Column(
                K.PROVENANCE,
                "Longest quotation, in characters, that the project allows itself from the source outside contract "
                "clauses. A self-imposed restraint, not a legal threshold or safe harbour.",
            ),
            "domains": Column(
                K.PROVENANCE, "Hosts that belong to the source. Left empty for sources whose policy forbids links."
            ),
            "ai_training": Column(K.PROVENANCE, "The source's published AI-training signal, if any."),
            "sebi_registration": Column(K.READ_FROM_SOURCE, "SEBI registration number, as SEBI's register prints it."),
            "terms_reviewed_on": Column(K.PROVENANCE, "When the project last read the source's terms and robots.txt."),
            "terms_summary": Column(
                K.ANNOTATION,
                "The project's summary of the source's terms as reviewed. Not legal advice.",
                rights=PROJECT_TEXT,
            ),
            "notes": NOTE,
        },
    ),
    "documents": Table(
        "One row per exact file, identified by its SHA-256. A revised file at the same address is a new row. Source "
        "documents are not distributed; the URL and hash let anyone obtain and confirm the same file.",
        {
            "id": Column(K.IDENTIFIER, "Id of the document."),
            "source": Column(K.IDENTIFIER, "Id of the publisher in `sources.csv`."),
            "type": Column(K.ANNOTATION, "What kind of document it is, from a closed list."),
            "title": Column(
                K.READ_FROM_SOURCE,
                "The title the file prints, or a descriptive title where it has none.",
                licensed=False,
                rights="A document's title as its publisher gives it, not licensed by the project.",
            ),
            "url": Column(K.PROVENANCE, "Address the file was retrieved from."),
            "landing_page": Column(K.PROVENANCE, "Page that lists or links the file, where known."),
            "retrieved_at": Column(K.PROVENANCE, "When the project retrieved the file (UTC)."),
            "retrieved_manually": Column(
                K.PROVENANCE,
                "True if a person downloaded the file in a browser and it was ingested by hash; false if the project's "
                "identified pipeline retrieved it.",
            ),
            "source_retrieval_policy": Column(
                K.PROVENANCE, "The publisher's current retrieval policy (`sources.csv`)."
            ),
            "sha256": Column(K.PROVENANCE, "SHA-256 of the exact file. Evidence is verified against this file only."),
            "size_bytes": Column(K.PROVENANCE, "Size of the file in bytes."),
            "media_type": Column(K.PROVENANCE, "Media type the server gave."),
            "pages": Column(K.PROVENANCE, "Number of pages in the file."),
            "dated": Column(K.READ_FROM_SOURCE, "The date the document gives itself."),
            "dated_basis": Column(K.PROVENANCE, "How the date was established."),
            "signed": Column(K.READ_FROM_SOURCE, "The date the document says it was signed."),
            "published": Column(
                K.READ_FROM_SOURCE,
                "The date the publisher says the file was posted, for example on its listing page. A server's "
                "Last-Modified header is never recorded here.",
                empty="the publisher states no date for the file, as for all but one file in this release",
            ),
            "published_basis": Column(K.PROVENANCE, "Where the publication date was read."),
            "last_modified": Column(
                K.PROVENANCE,
                "The server's Last-Modified header for the exact file held. It dates that version on the server. It "
                "does not establish first publication: a file can be uploaded before it is linked, replaced later, or "
                "copied with a misleading date.",
                empty="the server sent no Last-Modified header",
            ),
            "available_not_before": Column(
                K.DERIVED,
                "Lower bound: the file cannot have been public before this day, if the dates it prints are right. The "
                'latest of its own date, its signature or "as on" date, the date of a letter in it, and the latest '
                "event its rows report.",
                empty="no lower bound: the record reads no date from the file",
            ),
            "available_not_before_basis": Column(K.DERIVED, "Which kind of date gives the lower bound."),
            "available_from": Column(
                K.DERIVED,
                "A conservative estimate of when this exact file was at its address, not a publication date and not "
                "confirmed: the later of the publisher's date and Last-Modified, never before the lower bound; failing "
                "both, the lower bound; failing that, the confirmation date. It can still be early when a server's "
                "date predates the file's appearance. Used by `--as-of` with estimated availability.",
                empty="no date of any kind is known for the file",
            ),
            "available_basis": Column(K.DERIVED, "Which date `available_from` rests on."),
            "available_confirmed_by": Column(
                K.PROVENANCE,
                "The day the project retrieved the file from its public address, so it was public by then. The only "
                "availability date the record proves, and usually much later than first publication. Used by "
                "`--as-of` with `--availability observed`.",
                empty="the project never retrieved the file",
            ),
            "available_window_days": Column(
                K.DERIVED,
                "Days from the lower bound to the confirmation: the interval within which the file first became "
                "public.",
                empty="the lower bound or the confirmation is unknown, so the interval is open",
            ),
            "period_start": PERIOD_START,
            "period_end": PERIOD_END,
            "as_of": Column(K.READ_FROM_SOURCE, 'The "status as on" date a report prints.'),
            "supersedes": Column(K.ANNOTATION, "Earlier documents this file replaces, as identified by the project."),
            "regulatory_basis": Column(K.ANNOTATION, "The rule under which the document is published."),
            "ai_training_reserved": AI_RESERVED,
        },
    ),
    "issuers": Table(
        "One row per legal entity that issued an instrument in the sample.",
        {
            "id": Column(K.IDENTIFIER, "Id of the issuer."),
            "name": Column(
                K.ANNOTATION,
                "The name the project uses for the issuer, taken from a source.",
                licensed=False,
                rights=TRADE_NAME,
            ),
            "cin": Column(
                K.READ_FROM_SOURCE,
                "Corporate Identity Number, where a source prints one; `attribute_support.csv` says which.",
                empty="no record of the dataset prints one",
            ),
            "lei": Column(
                K.READ_FROM_SOURCE,
                "Legal Entity Identifier, where a source prints one; `attribute_support.csv` says which.",
                empty="no record of the dataset prints one",
            ),
            "sector": Column(K.ANNOTATION, "Sector, where classified. Empty in this release."),
            "name_variants": Column(
                K.READ_FROM_SOURCE,
                "Other names under which sources print the issuer.",
                licensed=False,
                rights=TRADE_NAME,
            ),
            "established_from": Column(
                K.DERIVED,
                "Earliest estimated day on which a record supporting the issuer was public (see "
                "`attribute_support.csv`).",
            ),
            "established_confirmed_by": Column(
                K.DERIVED, "Earliest day on which the project itself saw a record supporting the issuer."
            ),
        },
    ),
    "attribute_support": Table(
        "One row per record that establishes an attribute of an instrument or issuer, with when that record was "
        "public. An instrument's `identity` is its ISIN with the issuer the dataset assigns it to, established by any "
        "record printing the ISIN. An issuer's `name`, `cin` and `lei` are established only by records that print "
        "them. Point-in-time views show an attribute only once one of its supports is public.",
        {
            "entity": Column(K.IDENTIFIER, "`instrument` or `issuer`."),
            "key": Column(K.IDENTIFIER, "The ISIN or the issuer id.", type="string"),
            "attribute": Column(K.DERIVED, "`identity`, `name`, `cin` or `lei`."),
            "record": Column(K.PROVENANCE, "The record that prints the attribute."),
            "document": Column(
                K.IDENTIFIER, "The document the record is in.", empty="the support is an observation, not a document"
            ),
            "observed_at_url": Column(
                K.PROVENANCE,
                "The page of a source whose terms forbid storing it, where the value was seen.",
                empty="the support is a document",
            ),
            "available_from": Column(
                K.DERIVED, "Estimated day the supporting document was public, or the day the observation was made."
            ),
            "available_confirmed_by": Column(
                K.DERIVED, "Day the project retrieved the supporting document, or made the observation."
            ),
        },
    ),
    "instruments": Table(
        "One row per ISIN in the sample, summarising what the other tables hold about it.",
        {
            "isin": ISIN,
            "issuer": Column(K.IDENTIFIER, "Id of the issuer in `issuers.csv`."),
            "issuer_name": Column(
                K.DERIVED, "The issuer's name from `issuers.csv`.", licensed=False, rights=TRADE_NAME
            ),
            "trustees_claimed": Column(
                K.DERIVED,
                "Every trustee a claim names for the ISIN. More than one means sources disagree.",
                empty="no record names the ISIN's trustee",
            ),
            "trustee_claims_conflict": Column(K.DERIVED, "True when claims name more than one trustee."),
            "offer_documents": Column(
                K.DERIVED,
                "Linked offer documents (general or key information documents, placement memoranda) that have been "
                "retrieved. They give the terms as offered, not the executed deed. None in this release.",
                empty="none retrieved; absence is a fact about the project's access, not about the instrument",
            ),
            "executed_deeds": Column(
                K.DERIVED,
                "Linked debenture trust deeds and supplemental deeds that have been retrieved. None in this release.",
                empty="none retrieved; absence is a fact about the project's access, not about the instrument",
            ),
            "provisions": Column(K.DERIVED, "Number of clause records attached to the ISIN."),
            "trust_deed_dates": Column(
                K.DERIVED,
                "Every deed date that trustees' letters cite for the ISIN.",
                origin="The executed deeds, as the trustee describes them. No deed has been retrieved.",
            ),
            "established_from": Column(
                K.DERIVED,
                "Earliest estimated day on which a record printing the ISIN was public (`attribute_support.csv`).",
            ),
            "established_confirmed_by": Column(
                K.DERIVED, "Earliest day on which the project itself saw a record printing the ISIN."
            ),
            "notes": NOTE,
        },
    ),
    "claims": Table(
        "One row per attributed statement about one attribute of an instrument. Claims are never overwritten: where "
        "sources disagree, both rows stay and a discrepancy explains the disagreement.",
        {
            "isin": ISIN,
            "property": Column(K.ANNOTATION, "Which attribute the claim is about."),
            "value": Column(
                K.READ_FROM_SOURCE,
                "The value the source asserts. For `debenture_trustee`, the id of the trustee in `sources.csv`.",
                type="string",
            ),
            "asserted_by": Column(K.IDENTIFIER, "The source making the claim, in `sources.csv`."),
            "as_of": Column(K.READ_FROM_SOURCE, "The date the source gives for the value, where it gives one."),
            "evidence": EVIDENCE,
            "observed_at_urls": OBSERVED_AT,
            "note": NOTE,
        },
    ),
    "document_links": Table(
        "One row per document tied to an ISIN, with the reason the link holds.",
        {
            "isin": ISIN,
            "document": DOCUMENT,
            "role": Column(K.ANNOTATION, "What the document is for, relative to the ISIN."),
            "basis": Column(K.ANNOTATION, "Why the link holds, for example because the ISIN is printed in it."),
            "confidence": Column(K.ANNOTATION, "The project's confidence in the link."),
            "evidence": EVIDENCE,
            "note": NOTE,
        },
    ),
    "provisions": Table(
        "One row per contractual undertaking as quoted by some document. Only `stage = executed_text` is the "
        "contract's own wording, and no such record exists in this release.",
        {
            "id": Column(K.IDENTIFIER, "Id of the clause record."),
            "document": DOCUMENT,
            "document_type": Column(K.DERIVED, "Type of the quoting document, from `documents.csv`."),
            "clause": Column(K.READ_FROM_SOURCE, "Clause number as printed, or a note that none is given."),
            "heading": Column(K.SOURCE_TEXT, "The heading the clause sits under in the quoting document."),
            "page": PAGE,
            "category": Column(K.ANNOTATION, "Covenant category of SEBI's guidance note (Annex-VIA), or `other`."),
            "metric": Column(K.ANNOTATION, "What the limit measures, in plain words."),
            "thresholds": Column(
                K.ANNOTATION,
                "Parsed limits as JSON: comparator, value, unit and any dates they apply between. Parsed only where "
                "the wording is unambiguous.",
                empty="no limit parsed: none is stated, or the wording is not unambiguous",
            ),
            "test_frequency": Column(K.ANNOTATION, "How often the clause is tested, where stated."),
            "test_basis": Column(K.ANNOTATION, "Standalone or consolidated, where stated."),
            "instruments": Column(K.ANNOTATION, "ISINs the clause record is attached to."),
            "amends": Column(K.ANNOTATION, "The earlier clause record this one replaces."),
            "effective_from": Column(K.READ_FROM_SOURCE, "When the clause takes effect, where stated."),
            "stage": Column(
                K.ANNOTATION,
                "What the record is evidence of, one of four legal stages or a party's description: `offered` "
                "(quoted from an offer document), `proposed` (a change put forward), `approved_in_principle` (a "
                "change approved, not shown executed), `executed_text` (quoted from an executed deed), or "
                "`described_in_force` (a party's quotation or description of a term it treats as in force).",
            ),
            "text": Column(
                K.SOURCE_TEXT,
                "The clause as the quoting document prints it, up to 800 characters.",
                origin="The contract, as quoted or described by the publishing party; only executed text is the "
                "contract's own.",
            ),
            "explanation": Column(
                K.ANNOTATION,
                "A plain-English gloss written from the quoted text. Not legal advice.",
                rights=PROJECT_TEXT,
            ),
            "annotation_reviewed": Column(
                K.PROVENANCE, "Whether a second person has reviewed the record's annotations. False throughout."
            ),
            "ai_training_reserved": AI_RESERVED,
        },
    ),
    "breach_report_items": Table(
        "One row per trustee breach report, printed row, ISIN and covenant cell (Annex-VIIA, Table 5).",
        {
            "report": REPORT,
            "trustee": TRUSTEE,
            "period_end": PERIOD_END,
            "as_of": Column(K.READ_FROM_SOURCE, 'The report\'s printed "status as on" date.'),
            "supersedes": Column(K.ANNOTATION, "Earlier versions of the report that this one replaces."),
            "row": Column(
                K.READ_FROM_SOURCE,
                "Serial number as printed. A printed row split into several records keeps its number.",
                type="string",
            ),
            "issuer": Column(K.ANNOTATION, "Issuer record the row is assigned to."),
            "issuer_name_as_reported": Column(K.SOURCE_TEXT, "The issuer's name as the row prints it."),
            "isin": ISIN,
            "assignment_uncertain": Column(
                K.ANNOTATION, "True when which row the ISIN belongs to depends on reading merged table cells."
            ),
            "category": Column(K.ANNOTATION, "Covenant category of SEBI's guidance note (Annex-VIA), or `other`."),
            "specificity": Column(
                K.ANNOTATION,
                "How much of the term the cell prints: `clause_text`, `requirement_and_actual`, "
                "`clause_number_only` or `description_only`.",
            ),
            "clause_reference_as_reported": Column(
                K.SOURCE_TEXT, "Clause reference as printed.", origin="The deed's numbering, as the trustee cites it."
            ),
            "covenant_as_reported": Column(
                K.SOURCE_TEXT,
                "The covenant cell as printed, cut to the source's quotation limit.",
                origin="The deed's wording where the trustee quotes it (`specificity = clause_text`); otherwise the "
                "trustee's own description.",
            ),
            "covenant_truncated": Column(K.PROVENANCE, "True when the printed cell continues beyond the quotation."),
            "levels_stated": Column(
                K.READ_FROM_SOURCE,
                "Every percentage, multiple and crore amount printed anywhere in the cell, including the part not "
                "quoted.",
                empty="the cell prints no level",
                origin="Mixed: required levels come from the deed and actual levels from the issuer's measurement; "
                "the column does not say which is which.",
            ),
            "page": PAGE,
            "actual_breach_as_reported": Column(
                K.SOURCE_TEXT, "Date of actual breach as printed.", origin=TRUSTEE_ORIGIN_DATES
            ),
            "actual_breach": Column(
                K.READ_FROM_SOURCE,
                "Date of actual breach as read. Meaning differs by trustee; do not compare across.",
                empty="not printed, or the printed text is not one date",
            ),
            "detected_as_reported": Column(
                K.SOURCE_TEXT,
                "Date of detection as printed.",
                origin="The trustee's own record. IDBI defines it as the day it received the issuer's certificate.",
            ),
            "detected": Column(
                K.READ_FROM_SOURCE,
                "Date of detection as read.",
                empty="not printed, or the printed text is not one date",
            ),
            "first_intimation": Column(K.DERIVED, "Earliest date of intimation read from the row."),
            "intimation_as_reported": Column(K.SOURCE_TEXT, "Dates of intimation, and to whom, as printed."),
            "delay_in_detection_as_reported": Column(K.SOURCE_TEXT, "The report's own delay column, as printed."),
            "delay_in_intimation_as_reported": Column(K.SOURCE_TEXT, "The report's own delay column, as printed."),
            "delay_reasons_as_reported": Column(K.SOURCE_TEXT, "Reasons for delay, as printed."),
            "further_action_as_reported": Column(
                K.SOURCE_TEXT,
                "Action taken or proposed, as printed.",
                origin="The trustee's account of what it, the holders or the issuer did.",
            ),
            "truncated_fields": Column(K.PROVENANCE, "Fields whose printed cell continues beyond the quotation."),
            "other_columns_as_reported": Column(
                K.SOURCE_TEXT, "Columns the trustee prints beyond the prescribed format, as JSON keyed by heading."
            ),
            "actions": Column(K.ANNOTATION, "The project's reading of the action cells, from a closed list."),
            "transcribed_from_rendering": Column(
                K.PROVENANCE, "True when some cells are absent from the file's text layer and were read from the page."
            ),
            "linked_provisions": Column(K.ANNOTATION, "Clause records the project links to the cell."),
            "provision_agreement": Column(K.ANNOTATION, "Whether each linked clause agrees with the cell."),
            "ai_training_reserved": AI_RESERVED,
        },
    ),
    "no_information_entries": Table(
        "One row per issuer that a trustee's report says it has received no information about.",
        {
            "report": REPORT,
            "trustee": TRUSTEE,
            "period_end": PERIOD_END,
            "issuer_name_as_reported": Column(K.SOURCE_TEXT, "The issuer's name as printed."),
            "issuer": Column(K.ANNOTATION, "Issuer record matched to the name, where one exists."),
            "page": PAGE,
        },
    ),
    "breach_notices": Table(
        "One row per trustee letter to the holders of an instrument about a breach, or continuing an adjourned "
        "meeting.",
        {
            "id": Column(K.IDENTIFIER, "Id of the letter record."),
            "document": DOCUMENT,
            "page": PAGE,
            "trustee": TRUSTEE,
            "kind": Column(K.ANNOTATION, "`breach` or `meeting_continuation`."),
            "isins": Column(K.READ_FROM_SOURCE, "ISINs the letter concerns."),
            "isins_printed": Column(
                K.PROVENANCE, "False when the letter prints no ISIN and the link comes from elsewhere (see notes)."
            ),
            "issued_on": Column(K.READ_FROM_SOURCE, "The letter's date."),
            "period_end": Column(
                K.ANNOTATION,
                "Quarter-end the letter concerns, where stated or evident.",
                empty="the letter names no quarter, as letters continuing an adjourned meeting do",
            ),
            "deed_dates": Column(
                K.READ_FROM_SOURCE,
                "Dates of the trust deeds the letter cites.",
                origin="The executed deeds, as the trustee describes them.",
            ),
            "deed_as_reported": Column(K.SOURCE_TEXT, "The sentence citing the deeds."),
            "issuer_intimation": Column(
                K.READ_FROM_SOURCE,
                "When the trustee says the issuer informed it.",
                origin="The trustee's record of receipt.",
            ),
            "meeting_proposed_for": Column(K.READ_FROM_SOURCE, "Date proposed for a meeting of holders."),
            "clause_reference_as_reported": Column(K.SOURCE_TEXT, "Clause reference as printed."),
            "covenant_as_reported": Column(
                K.SOURCE_TEXT,
                "The covenant passage as printed, cut to the quotation limit.",
                origin="The deed's wording, as the trustee quotes or describes it.",
            ),
            "covenant_truncated": Column(K.PROVENANCE, "True when the passage continues beyond the quotation."),
            "levels_stated": Column(
                K.READ_FROM_SOURCE, "Every percentage, multiple and crore amount printed in the whole passage."
            ),
            "adjourned_for_lack_of_quorum": Column(
                K.READ_FROM_SOURCE, "True when the letter says a meeting was adjourned for lack of quorum."
            ),
            "read_from_rendering": Column(K.PROVENANCE, "True when the file has no usable text layer for the letter."),
            "notes": NOTE,
            "ai_training_reserved": AI_RESERVED,
        },
    ),
    "notice_report_comparisons": Table(
        "One row per ISIN for which a trustee's report row and the same trustee's letter for the same quarter can be "
        "compared. Both come from the trustee, so agreement is not independent corroboration.",
        {
            "notice": Column(K.IDENTIFIER, "Id of the letter in `breach_notices.csv`."),
            "isin": ISIN,
            "report": REPORT,
            "row": Column(K.READ_FROM_SOURCE, "Serial number of the report row compared.", type="string"),
            "issuer_intimation_per_notice": Column(K.READ_FROM_SOURCE, "When the letter says the issuer told it."),
            "detected_per_report": Column(K.READ_FROM_SOURCE, "Detection date the report prints."),
            "days_from_intimation_to_detection": Column(K.DERIVED, "Detection minus intimation, in days."),
            "thresholds_in_notice": Column(K.DERIVED, "Levels printed in the letter."),
            "thresholds_in_report": Column(K.DERIVED, "Levels printed in the report row for the ISIN."),
            "thresholds_agree": Column(
                K.DERIVED,
                "Whether the two sets of numbers match.",
                empty="not applicable: the letter prints no level, or only part of its passage was read",
            ),
        },
    ),
    "compliance_statements": Table(
        "One row per explicit statement about covenant compliance, for stated instruments and a period. The statement "
        "belongs to whoever made it; the project does not adopt it.",
        {
            "id": Column(K.IDENTIFIER, "Id of the statement."),
            "document": DOCUMENT,
            "instruments": Column(
                K.ANNOTATION, "ISINs the statement covers, by printing them or by a general sentence."
            ),
            "period_start": PERIOD_START,
            "period_end": PERIOD_END,
            "stated_by": Column(K.IDENTIFIER, "The source that published the statement: the carrier."),
            "made_by": Column(
                K.READ_FROM_SOURCE,
                "Who made the statement: `issuer` or `statutory_auditor`.",
                origin="The conclusion originates with this party, whoever publishes it.",
            ),
            "scope": Column(K.READ_FROM_SOURCE, "What the statement says it covers: all covenants or financial only."),
            "breach_stated": Column(K.READ_FROM_SOURCE, "True when the statement says some covenant was not met."),
            "isins_printed": Column(
                K.ANNOTATION, "False when the statement reaches an ISIN only by a general sentence or by omission."
            ),
            "exceptions": Column(K.DERIVED, "Number of exception lines in `compliance_statement_exceptions.csv`."),
            "evidence": EVIDENCE,
            "note": NOTE,
        },
    ),
    "compliance_statement_exceptions": Table(
        "One row per line a compliance statement lists as not met.",
        {
            "statement": STATEMENT,
            "document": DOCUMENT,
            "page": PAGE,
            "isins": Column(K.READ_FROM_SOURCE, "ISINs the line names."),
            "covenant_as_reported": Column(K.SOURCE_TEXT, "The covenant as printed."),
            "required_as_reported": Column(
                K.SOURCE_TEXT, "The required level as printed.", origin="The deed, as the issuer states it."
            ),
            "actual_as_reported": Column(
                K.SOURCE_TEXT, "The measured level as printed.", origin="The issuer's measurement from its own books."
            ),
            "deed_dates_as_reported": Column(K.SOURCE_TEXT, "Deed dates as printed."),
            "read_from_rendering": Column(K.PROVENANCE, "True when the line was read from the rendered page."),
        },
    ),
    "statement_report_comparisons": Table(
        "One row per statement and ISIN, set beside the current trustee report for the same quarter. Agreement shows "
        "that the statement was carried into the report, not that it was confirmed.",
        {
            "statement": STATEMENT,
            "isin": ISIN,
            "period_end": PERIOD_END,
            "made_by": Column(K.READ_FROM_SOURCE, "Who made the statement."),
            "scope": Column(K.READ_FROM_SOURCE, "What the statement says it covers."),
            "statement_reports_breach": Column(K.READ_FROM_SOURCE, "True when the statement reports a breach."),
            "trustee_report": Column(K.IDENTIFIER, "The trustee report compared, if one exists."),
            "trustee_lists": Column(
                K.DERIVED,
                "Whether that report lists the ISIN.",
                empty="not comparable: no fully transcribed report of the ISIN's trustee for the period",
            ),
            "agreement": Column(
                K.DERIVED, "`consistent`, `differs` or `not_comparable`, by rules in docs/data-model.md."
            ),
            "basis": Column(K.DERIVED, "Which rule decided the agreement."),
            "levels_only_in_statement": Column(
                K.DERIVED, "Required levels the statement prints and the trustee's report does not print for the ISIN."
            ),
            "statement_dated": Column(K.READ_FROM_SOURCE, "The statement document's own date."),
            "trustee_received_report": Column(
                K.READ_FROM_SOURCE,
                "When the trustee records receiving the issuer's quarterly compliance report, from its census table.",
                origin="The trustee's record of receipt.",
                empty="no census of the trustee for the period has been measured, or it has no row cited for the ISIN",
            ),
            "trustee_detected": Column(
                K.READ_FROM_SOURCE, "The trustee's earliest printed detection date for the ISIN."
            ),
            "trustee_cites_certificate": Column(
                K.DERIVED, "True when the trustee's row mentions a certificate or auditor (a mechanical text match)."
            ),
            "trustee_could_rely_on_issuer": Column(
                K.DERIVED,
                "True when the trustee's detection falls on or after the statement's date or the trustee's receipt of "
                "the issuer's report, so the trustee may simply be passing the issuer's information on.",
            ),
        },
    ),
    "field_flows": Table(
        "For each agreement between an issuer's statement and a trustee's report on a breach, one row per kind of "
        "information, saying which party prints it, with every line, item or letter that satisfied the mechanical "
        "rule (docs/methods.md). The 17 agreements come from two issuers; this is not the wider statement comparison "
        "in `statement_report_comparisons.csv`, nor the comparison sample's pilot.",
        {
            "statement": STATEMENT,
            "isin": ISIN,
            "period_end": PERIOD_END,
            "trustee_report": REPORT,
            "field": Column(
                K.DERIVED,
                "Kind of information: clause reference, obligation wording, required level, issuer's measured level, "
                "deed dates.",
            ),
            "issuer_prints": Column(
                K.DERIVED, "Whether any of the statement's exception lines for the ISIN prints it."
            ),
            "trustee_prints": Column(
                K.DERIVED,
                "Whether any of the trustee's report items for the ISIN, or for deed dates its letters for the "
                "quarter, prints it. The issuer's measured level counts only if the trustee prints the same number "
                "and unit.",
            ),
            "issuer_examined": Column(
                K.DERIVED, "How many of the statement's exception lines for the ISIN were examined."
            ),
            "issuer_evidence": Column(
                K.DERIVED,
                "JSON list of every exception line that satisfied the rule: document, page, locator and the text "
                "that matched.",
                licensed=False,
                rights=FLOW_RIGHTS,
                empty="no line satisfied the rule; `issuer_examined` says how many were looked at",
            ),
            "trustee_examined": Column(
                K.DERIVED, "How many report items, or for deed dates letters for the quarter, were examined."
            ),
            "trustee_evidence": Column(
                K.DERIVED,
                "JSON list of every report item or letter that satisfied the rule: document, page, locator and the "
                "text that matched.",
                licensed=False,
                rights=FLOW_RIGHTS,
                empty="nothing satisfied the rule; `trustee_examined` says how many were looked at, and 0 means the "
                "record holds nothing to examine, not that the trustee printed nothing",
            ),
            "ai_training_reserved": AI_RESERVED,
        },
    ),
    "follow_up_states": Table(
        "For each ISIN listed in a current trustee report for a period, one row per follow-up state that the trustee's "
        "reports and letters publish, with where the record shows it and how its period is known. A listed ISIN with "
        "none has one row reading `no follow-up published`. Rows with no period come from letters that name no quarter "
        "and cannot be tied to one. States are never ranked or merged.",
        {
            "trustee": TRUSTEE,
            "isin": ISIN,
            "period_end": Column(
                K.DERIVED,
                "The reporting period the state is counted for.",
                empty="the letter names no quarter and the rule cannot tie it to one; counted for no period",
            ),
            "state": Column(
                K.DERIVED,
                "The state, from the project's reading of action cells and letters. A cure is typed financial or other "
                "only when every covenant the row lists for the ISIN is of that kind; otherwise it is a cure for "
                "covenants of more than one kind.",
            ),
            "is_outcome": Column(
                K.DERIVED,
                "True for the six outcome states: enforcement or nominee director, waiver, holders instructing no "
                "action, and the three kinds of cure.",
            ),
            "attribution": Column(
                K.DERIVED,
                "How the period is known: `report_row` (a row of the period's report), `letter_period` (the quarter "
                "recorded for the letter), `linked_by_rule` (a letter naming no quarter, continuing a letter of the "
                "same file that names one) or `not_attributable`.",
            ),
            "basis": Column(
                K.DERIVED,
                "The report row and action kinds, or the letter, that show the state, and for linked letters the rule.",
                empty="no follow-up is published for the ISIN",
            ),
        },
    ),
    "monitoring_censuses": Table(
        "One row per trustee table of the issues it monitors (Annex-VIIA, Table 3), measured rather than republished. "
        "`brdo verify` recomputes every measure from the hashed file.",
        {
            "id": Column(K.IDENTIFIER, "Id of the census record."),
            "document": DOCUMENT,
            "trustee": TRUSTEE,
            "period_start": PERIOD_START,
            "period_end": PERIOD_END,
            "isins_printed": Column(K.DERIVED, "Distinct ISINs printed in the file that pass the check digit."),
            "listed_in_breach_report": Column(
                K.DERIVED, "ISINs the same trustee's breach report for the period lists."
            ),
            "listed_not_printed": Column(K.DERIVED, "Listed ISINs the census omits."),
            "sample": Column(
                K.DERIVED,
                "ISINs outside the breach report whose SHA-256 of the file's hash, a colon and the ISIN sorts first.",
            ),
            "report_not_received": Column(
                K.DERIVED,
                "ISINs whose census row marks the issuer's quarterly compliance report as not received. Whether that "
                "breaches an instrument's terms depends on its deed.",
            ),
            "rows_cited": Column(K.DERIVED, "Number of census rows the dataset quotes."),
            "ai_training_reserved": AI_RESERVED,
        },
    ),
    "regulatory_references": Table(
        "One row per checked passage of a regulation or circular that the design relies on.",
        {
            "id": Column(K.IDENTIFIER, "Id of the passage."),
            "document": DOCUMENT,
            "page": PAGE,
            "quote": Column(K.SOURCE_TEXT, "The passage, verbatim."),
            "relevance": Column(K.ANNOTATION, "Why the project relies on it.", rights=PROJECT_TEXT),
        },
    ),
    "instrument_status": Table(
        "One row per ISIN and reporting period: what the reviewed record says about breaches, and on what basis. "
        "`no_report_found` is never evidence of compliance, and no status implies another.",
        {
            "isin": ISIN,
            "period_end": Column(K.DERIVED, "End of the reporting period."),
            "status": Column(K.DERIVED, "Status from a closed list; see docs/data-model.md."),
            "basis": Column(K.DERIVED, "The rule that produced the status, including which kind of absence it is."),
            "documents": Column(
                K.DERIVED,
                "Documents the status rests on.",
                empty="the status rests on no document, as for not_assessed",
            ),
        },
    ),
    "searches": Table(
        "One row per documented attempt to find something, successful or not. A `not_found` means not found by the "
        "logged step on that date.",
        {
            "id": Column(K.IDENTIFIER, "Id of the search."),
            "performed_on": Column(K.PROVENANCE, "When the search was made."),
            "subject": Column(K.IDENTIFIER, "ISIN, issuer id or source id the search was about."),
            "purpose": Column(K.PROVENANCE, "What was sought."),
            "channel": Column(K.PROVENANCE, "Web search, a source's listing page, or a direct address."),
            "query": Column(
                K.PROVENANCE,
                "The query, for web searches. Results can differ when re-run. Some search for covenant wording a "
                "trustee quotes.",
                rights=PROJECT_TEXT,
            ),
            "scope": Column(K.PROVENANCE, "Sites or pages searched."),
            "period_end": Column(K.PROVENANCE, "End of the reporting period sought, where one was."),
            "outcome": Column(K.ANNOTATION, "The project's classification of the result."),
            "documents": Column(K.IDENTIFIER, "Documents found and registered."),
            "urls_seen": Column(K.PROVENANCE, "Candidates seen but not retrieved, such as manual-only sources."),
            "note": NOTE,
        },
    ),
    "discrepancies": Table(
        "One row per disagreement or oddity in the public record, kept open until resolved. Nothing here is a finding "
        "about anyone's conduct.",
        {
            "id": Column(K.IDENTIFIER, "Id of the discrepancy."),
            "kind": Column(K.ANNOTATION, "What kind of disagreement it is."),
            "subject": Column(K.IDENTIFIER, "ISINs, issuer or source concerned."),
            "status": Column(K.ANNOTATION, "`open` or `resolved`."),
            "description": Column(K.ANNOTATION, "The project's neutral description.", rights=PROJECT_TEXT),
            "evidence": EVIDENCE,
            "observed_at_urls": OBSERVED_AT,
            "resolution": Column(K.ANNOTATION, "How it was resolved, if it was."),
        },
    ),
    "evidence": Table(
        "One row per evidence anchor: a document, a page and the words relied on. `brdo verify` re-tests each against "
        "the hashed file.",
        {
            "used_by": Column(K.PROVENANCE, "Which record relies on the anchor."),
            "document": DOCUMENT,
            "page": Column(K.PROVENANCE, "1-based page of the file; empty when the anchor may be on any page."),
            "locator": Column(K.PROVENANCE, "A human-readable position, where given."),
            "quote": Column(K.SOURCE_TEXT, "The words relied on, verbatim."),
            "read_from_rendering": Column(
                K.PROVENANCE,
                "True when the words were read from the rendered page because the text layer may lack them. Such an "
                "anchor is machine-verified only if the words are found in the text layer anyway.",
            ),
            "ai_training_reserved": AI_RESERVED,
        },
    ),
}


def undocumented(all_tables: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Exported tables and columns with no description, and descriptions of columns that are no longer exported."""
    problems = []
    for name, rows in all_tables.items():
        documented = TABLES.get(name)
        if documented is None:
            problems.append(f"table {name} is not documented")
            continue
        exported = list(rows[0]) if rows else list(documented.columns)
        problems += [f"{name}.{column} is not documented" for column in exported if column not in documented.columns]
        problems += [
            f"{name}.{column} is documented but not exported" for column in documented.columns if column not in exported
        ]
    problems += [f"table {name} is documented but not exported" for name in TABLES if name not in all_tables]
    return problems


_PATTERNS = (
    ("boolean", re.compile(r"^(?:true|false)$")),
    ("integer", re.compile(r"^-?\d+$")),
    ("number", re.compile(r"^-?\d+\.\d+$")),
    ("date", re.compile(r"^\d{4}-\d{2}-\d{2}$")),
    ("datetime", re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)$")),
)


def _infer_type(values: list[str]) -> str:
    present = [value for value in values if value != ""]
    if not present:
        return "string"
    for name, pattern in _PATTERNS:
        if all(pattern.match(value) for value in present):
            return name
    return "string"


QUOTATION_RIGHTS = (
    "Verbatim text from a third-party source, quoted for research, review and verification. It remains its owner's and "
    "is not licensed under CC BY 4.0 or any other licence by this project; reuse it only as the source's terms and the "
    "law allow."
)
LICENCE_NOTE = (
    "The project's own work (structure, facts it records, annotations, derived values and measurements) is under "
    "CC BY 4.0. That licence does not cover any field marked `brdo:licensed: false` (kind `source_text`), which holds "
    "third-party quotations, nor any source document, none of which is included. See LICENSE-DATA.md."
)


def datapackage(
    all_tables: dict[str, list[dict[str, Any]]], cited_sources: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    """A Frictionless Data Package descriptor for the CSV exports, built from the column descriptions."""
    resources = []
    for name, rows in all_tables.items():
        table = TABLES[name]
        fields = []
        for column, documented in table.columns.items():
            values = [str(row[column]) for row in rows]
            field = {
                "name": column,
                "type": documented.type or _infer_type(values),
                "description": documented.description,
                "brdo:kind": documented.kind.value,
                "brdo:licensed": documented.is_licensed,
            }
            if documented.kind is ColumnKind.SOURCE_TEXT or documented.rights:
                field["brdo:rights"] = documented.rights or QUOTATION_RIGHTS
            if documented.origin:
                field["brdo:origin"] = documented.origin
            if documented.empty:
                field["brdo:empty"] = documented.empty
            if any("; " in value for value in values):
                field["brdo:separator"] = "; "
            fields.append(field)
        resources.append(
            {
                "name": name.replace("_", "-"),
                "path": f"{name}.csv",
                "profile": "tabular-data-resource",
                "format": "csv",
                "mediatype": "text/csv",
                "encoding": "utf-8",
                "description": table.description,
                "schema": {"fields": fields, "missingValues": [""]},
            }
        )
    return {
        "profile": "tabular-data-package",
        "name": "bondholder-rights-observatory",
        "title": "Bondholder Rights & Disclosure Observatory",
        "description": (
            "Source-linked, instrument-level records of contractual protections and public disclosures for Indian "
            "listed non-convertible debentures. Every field is labelled `brdo:kind`: "
            + "; ".join(f"`{kind.value}`: {guide}" for kind, guide in KIND_GUIDE.items())
            + " `brdo:origin` says where a fact originates when that differs from the party that published it. "
            "Multi-valued cells are joined with `; `. The sample is selected on reported breaches and describes no "
            "market. Absence of a record is never evidence of compliance."
        ),
        "homepage": REPOSITORY_URL,
        "licenses": [
            {
                "name": "CC-BY-4.0",
                "path": "https://creativecommons.org/licenses/by/4.0/",
                "title": "Creative Commons Attribution 4.0, for the project's own work only; not for fields marked "
                "brdo:licensed false, which are third-party quotations",
            }
        ],
        "brdo:rights": LICENCE_NOTE,
        "sources": cited_sources or [],
        "resources": resources,
    }


def render_markdown() -> str:
    lines = [
        "# Data dictionary",
        "",
        "Generated by `brdo dictionary` from `src/brdo/dictionary.py`. It describes every column of the CSV files in "
        "[`exports/`](../exports), which `exports/datapackage.json` also describes in machine-readable form "
        "(Frictionless Data Package).",
        "",
        "Every column has one **kind**, so that a quotation, a fact read from a source, the project's own reading and "
        "a computed value are never confused:",
        "",
        "| kind | meaning |",
        "|---|---|",
        *[f"| `{kind.value}` | {guide} |" for kind, guide in KIND_GUIDE.items()],
        "",
        "Every fact is published by the party whose document carries it. Where the fact **originates** elsewhere, the "
        "origin is given. A trustee's report carries the issuer's measurement, for example, and agreement between two "
        "publications of one origin is transmission, not confirmation.",
        "",
        "Multi-valued cells are joined with `; `. Empty cells mean the value is absent from the record, which is "
        "never evidence that something did not happen.",
    ]
    lines += [
        "",
        "**Licence.** " + LICENCE_NOTE + " In `exports/datapackage.json` every quoted field carries "
        "`brdo:licensed: false` and a `brdo:rights` statement, so that software reading the data can tell.",
    ]
    for name, table in TABLES.items():
        lines += [
            "",
            f"## `{name}.csv`",
            "",
            table.description,
            "",
            "| column | kind | meaning | empty means | origin |",
        ]
        lines.append("|---|---|---|---|---|")
        for column, documented in table.columns.items():
            kind = documented.kind.value + ("" if documented.is_licensed else " (not licensed)")
            cells = [f"`{column}`", kind, documented.description, documented.empty or "", documented.origin or ""]
            lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
