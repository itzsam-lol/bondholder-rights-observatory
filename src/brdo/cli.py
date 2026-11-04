"""Command-line interface: ``brdo <command>``."""

import argparse
import json
import logging
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import yaml
from pypdf import PdfReader

from brdo import models
from brdo.build import tables, write_csv, write_sqlite
from brdo.fetch import Cache, Fetcher, RetrievalFailed, RetrievalRefused, Retrieved, default_cache_dir, source_for_url
from brdo.pdftext import normalize
from brdo.pit import as_of
from brdo.report import render_report
from brdo.status import derive_all
from brdo.store import DatasetError, Severity, check_integrity, load_dataset
from brdo.verify import (
    AnchorStatus,
    census_problems,
    load_document_text,
    summarize,
    text_layer_warnings,
    untranscribed_isins,
    verify_dataset,
)
from brdo.vocab import AvailabilityMode, DocumentType, RetrievalPolicy

DEFAULT_DATA = Path("data")


def _load(args: argparse.Namespace):
    try:
        return load_dataset(args.data)
    except DatasetError as error:
        for problem in error.problems:
            print(problem, file=sys.stderr)
        sys.exit(1)


def _fetcher(dataset, cache: Cache) -> Fetcher:
    return Fetcher(dataset.sources.values(), cache)


def cmd_validate(args: argparse.Namespace) -> int:
    dataset = _load(args)
    problems = check_integrity(dataset)
    for problem in problems:
        print(problem, file=sys.stderr)
    errors = sum(1 for problem in problems if problem.severity is Severity.ERROR)
    counts = ", ".join(
        f"{len(getattr(dataset, name))} {name.replace('_', ' ')}"
        for name in ("sources", "documents", "issuers", "instruments", "provisions", "breach_reports", "searches")
    )
    print(f"{counts}; {errors} errors, {len(problems) - errors} warnings")
    return 1 if errors else 0


def cmd_verify(args: argparse.Namespace) -> int:
    dataset = _load(args)
    cache = Cache(args.cache)
    fetcher = None if args.offline else _fetcher(dataset, cache)
    results = verify_dataset(dataset, cache, fetcher)
    failures = [result for result in results if not result.ok]
    for document_id, page, problem in text_layer_warnings(dataset, cache):
        print(f"text layer: {document_id} p{page}: {problem}")
    untranscribed = untranscribed_isins(dataset, cache, fetcher)
    for document_id, isin in untranscribed:
        print(f"untranscribed: {document_id} prints {isin}, which its transcription does not list")
    censuses = census_problems(dataset, cache, fetcher)
    for census_id, problem in censuses:
        print(f"census: {census_id}: {problem}")
    for result in failures:
        where = f"p{result.page}" if result.page else "-"
        found = f" (found on {list(result.found_on)})" if result.found_on else ""
        print(f"{result.status}: {result.document} {where}: {result.label}{found} {result.detail}".rstrip())
    for key, count in summarize(results).items():
        print(f"{count:6d}  {key}")
    hard_failures = [
        result for result in failures if not (args.offline and result.status is AnchorStatus.DOCUMENT_UNAVAILABLE)
    ]
    return 1 if hard_failures or untranscribed or censuses else 0


def cmd_fetch(args: argparse.Namespace) -> int:
    dataset = _load(args)
    fetcher = _fetcher(dataset, Cache(args.cache))
    status = 0
    for document in sorted(dataset.documents.values(), key=lambda d: d.id):
        if document.sha256 is None or (args.only and document.id not in args.only):
            continue
        if fetcher.cache.get(document.sha256):
            continue
        try:
            retrieved = fetcher.fetch(document.url)
        except (RetrievalRefused, RetrievalFailed) as error:
            print(f"{document.id}: {error}", file=sys.stderr)
            status = 1
            continue
        verdict = "ok" if retrieved.sha256 == document.sha256 else f"CHANGED at source (now {retrieved.sha256})"
        print(f"{document.id}: {verdict}")
        status |= int(retrieved.sha256 != document.sha256)
    return status


def _retrieve_for_record(args: argparse.Namespace, dataset, cache: Cache) -> tuple[str, Retrieved]:
    """Retrieve through the pipeline, or take a file downloaded in a browser from a manual-only source."""
    if not args.from_file:
        fetcher = _fetcher(dataset, cache)
        source = fetcher.check_allowed(args.url)
        return source.id, fetcher.fetch(args.url)
    source = source_for_url(args.url, dataset.sources.values())
    if source is None:
        raise RetrievalRefused(f"{args.url}: host is not a registered source; add it to sources.yaml first")
    if source.retrieval is RetrievalPolicy.EXCLUDED:
        raise RetrievalRefused(f"{args.url}: {source.id} is excluded by the project's source policy")
    body = args.from_file.read_bytes()
    retrieved_at = datetime.now(UTC).replace(microsecond=0)
    media_type = "application/pdf" if body.startswith(b"%PDF") else "text/html"
    sha256, path = cache.store(
        body, {"url": args.url, "retrieved_at": retrieved_at.isoformat(), "media_type": media_type, "manual": True}
    )
    return source.id, Retrieved(args.url, args.url, sha256, len(body), media_type, None, retrieved_at, path)


def cmd_add_document(args: argparse.Namespace) -> int:
    dataset = _load(args)
    if args.id in dataset.documents:
        print(f"document {args.id} already exists", file=sys.stderr)
        return 1
    cache = Cache(args.cache)
    try:
        source_id, retrieved = _retrieve_for_record(args, dataset, cache)
    except (RetrievalRefused, RetrievalFailed) as error:
        print(error, file=sys.stderr)
        return 1
    record = {
        "id": args.id,
        "source": source_id,
        "type": args.type,
        "title": args.title,
        "url": args.url,
        "retrieved_at": retrieved.retrieved_at,
        "sha256": retrieved.sha256,
        "size_bytes": retrieved.size_bytes,
        "media_type": retrieved.media_type,
    }
    if args.from_file:
        record["retrieved_manually"] = True
    if retrieved.media_type == "application/pdf":
        record["pages"] = len(PdfReader(retrieved.path).pages)
    if args.landing_page:
        record["landing_page"] = args.landing_page
    if retrieved.last_modified:
        record["dates"] = [
            {"kind": "last_modified", "value": retrieved.last_modified.date(), "basis": "http_last_modified"}
        ]
    with (args.data / "documents.yaml").open("a", encoding="utf-8") as handle:
        yaml.safe_dump([record], handle, sort_keys=False, allow_unicode=True, width=110)
    print(f"added {args.id}: {retrieved.sha256} ({retrieved.size_bytes} bytes)")
    return 0


def _document_pages(args: argparse.Namespace) -> list[str]:
    dataset = _load(args)
    document = dataset.documents.get(args.document)
    if document is None:
        sys.exit(f"unknown document {args.document}")
    cache = Cache(args.cache)
    text = load_document_text(document, cache, _fetcher(dataset, cache))
    if text.pages is None:
        sys.exit(f"{args.document}: {text.problem} {text.detail}")
    return text.pages


def cmd_find(args: argparse.Namespace) -> int:
    pages = _document_pages(args)
    target = normalize(args.text)
    hits = 0
    for number, page in enumerate(pages, start=1):
        flat = normalize(page)
        start = flat.find(target)
        while start != -1:
            hits += 1
            context = flat[max(0, start - 80) : start + len(target) + 80]
            print(f"p{number}: ...{context}...")
            start = flat.find(target, start + 1)
    return 0 if hits else 1


def cmd_page(args: argparse.Namespace) -> int:
    pages = _document_pages(args)
    if not 1 <= args.number <= len(pages):
        sys.exit(f"page {args.number} out of range 1..{len(pages)}")
    print(pages[args.number - 1])
    return 0


def cmd_audit_text(args: argparse.Namespace) -> int:
    dataset = _load(args)
    for document_id, page, problem in text_layer_warnings(dataset, Cache(args.cache)):
        print(f"{document_id} p{page}: {problem}")
    return 0


def cmd_scaffold_instruments(args: argparse.Namespace) -> int:
    """Create a minimal record for each ISIN a breach report lists but the dataset does not yet hold."""
    dataset = _load(args)
    cache = Cache(args.cache)
    fetcher = _fetcher(dataset, cache)
    directory = args.data / "instruments"
    created = 0
    for document_id in sorted(dataset.breach_reports):
        report = dataset.breach_reports[document_id]
        text = load_document_text(dataset.documents[document_id], cache, fetcher)
        pages = text.pages or []
        for row in report.rows:
            for item in row.items:
                for isin in item.isins:
                    path = directory / f"{isin}.yaml"
                    if isin in dataset.instruments or path.exists():
                        continue
                    found = [number for number, page in enumerate(pages, start=1) if isin in page]
                    evidence = {"document": document_id, "page": found[0] if found else item.page, "quote": isin}
                    if not found:
                        evidence["visual_fallback"] = True
                    record = {
                        "isin": isin,
                        "issuer": row.issuer,
                        "claims": [
                            {
                                "property": "debenture_trustee",
                                "value": report.trustee,
                                "asserted_by": report.trustee,
                                "evidence": [evidence],
                                "note": "Inferred from the trustee listing this ISIN in its own breach status report.",
                            }
                        ],
                    }
                    path.write_text(yaml.safe_dump(record, sort_keys=False, width=110), encoding="utf-8")
                    created += 1
    print(f"created {created} instrument records")
    return 0


def _as_of(args: argparse.Namespace, dataset):
    return as_of(dataset, args.as_of, AvailabilityMode(args.availability)) if args.as_of else dataset


def cmd_status(args: argparse.Namespace) -> int:
    dataset = _as_of(args, _load(args))
    for status in derive_all(dataset):
        print(f"{status.isin}  {status.period_end}  {status.status:<24} {status.basis}")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    dataset = _load(args)
    problems = [p for p in check_integrity(dataset) if p.severity is Severity.ERROR]
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    all_tables = tables(dataset)
    for path in write_csv(all_tables, args.out):
        print(f"wrote {path}")
    if args.sqlite:
        print(f"wrote {write_sqlite(all_tables, args.sqlite)}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    dataset = _load(args)
    text = render_report(dataset)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    dataset = _as_of(args, _load(args))
    instrument = dataset.instruments.get(args.isin)
    if instrument is None:
        print(f"no record for {args.isin}", file=sys.stderr)
        return 1
    issuer = dataset.issuers[instrument.issuer]
    print(f"{instrument.isin}  {issuer.name}")
    if dataset.cutoff is not None:
        print(
            f"  as of  {dataset.cutoff} ({dataset.availability_mode} availability): "
            f"{len(dataset.documents)} documents shown public by then, {len(dataset.withheld)} withheld"
        )
    for claim in instrument.claims:
        print(f"  claim  {claim.property}: {claim.value}  (asserted by {claim.asserted_by})")
    for link in instrument.documents:
        print(f"  doc    {link.document}  [{link.role}; {link.basis}; {link.confidence}]")
    for provision in sorted(dataset.provisions.values(), key=lambda p: p.id):
        if instrument.isin in provision.instruments:
            print(f"  clause {provision.document} {provision.clause} p{provision.page} [{provision.category}]")
            print(f"         {provision.text[:160]}")
    for report in dataset.breach_reports.values():
        for row in report.rows:
            for item in row.items:
                if instrument.isin in item.isins:
                    print(f"  report {report.document} row {row.row}: {item.covenant_as_reported[:120]}")
    for notice in sorted(dataset.breach_notices.values(), key=lambda n: n.issued_on):
        if instrument.isin in notice.isins:
            deeds = ", ".join(str(d) for d in notice.deed_dates) or "none cited"
            print(f"  notice {notice.document} p{notice.page} {notice.issued_on} [{notice.kind}]; deeds: {deeds}")
    for statement in sorted(dataset.compliance_statements.values(), key=lambda s: (s.period.end, s.id)):
        if instrument.isin in statement.instruments:
            says = "breach" if statement.breach_stated else "compliance"
            print(
                f"  stated {statement.document} {statement.period.end} "
                f"by {statement.made_by} ({statement.scope}): {says}"
            )
            for line in statement.exceptions:
                if instrument.isin in line.isins:
                    levels = " ".join(text for text in (line.required_as_reported, line.actual_as_reported) if text)
                    print(f"         {line.covenant_as_reported} {levels}".rstrip())
    for discrepancy in dataset.discrepancies.values():
        if instrument.isin in {part.strip() for part in discrepancy.subject.split(",")}:
            print(f"  {discrepancy.status:<6} {discrepancy.id}: {discrepancy.description[:120]}")
    for status in derive_all(dataset):
        if status.isin == instrument.isin:
            print(f"  status {status.period_end}: {status.status} ({status.basis})")
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    """Write a JSON Schema for each kind of record, for people working outside Python."""
    args.out.mkdir(parents=True, exist_ok=True)
    for name in sorted(vars(models)):
        record = getattr(models, name)
        if not (isinstance(record, type) and issubclass(record, models.Record) and record is not models.Record):
            continue
        schema = record.model_json_schema()
        (args.out / f"{name}.json").write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote schemas to {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brdo", description="Bondholder Rights & Disclosure Observatory")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="data directory (default: data)")
    parser.add_argument("--cache", type=Path, default=default_cache_dir(), help="document cache directory")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("validate", help="check records and cross-references").set_defaults(func=cmd_validate)

    verify = commands.add_parser("verify", help="re-check every evidence anchor against its document")
    verify.add_argument("--offline", action="store_true", help="use only cached documents")
    verify.set_defaults(func=cmd_verify)

    fetch = commands.add_parser("fetch", help="download recorded documents into the cache, checking hashes")
    fetch.add_argument("only", nargs="*", help="document ids (default: all)")
    fetch.set_defaults(func=cmd_fetch)

    add = commands.add_parser("add-document", help="retrieve a document and append its record")
    add.add_argument("url")
    add.add_argument("--id", required=True)
    add.add_argument("--type", required=True, choices=[t.value for t in DocumentType])
    add.add_argument("--title", required=True)
    add.add_argument("--landing-page")
    add.add_argument("--from-file", type=Path, help="a file downloaded from this URL in a browser")
    add.set_defaults(func=cmd_add_document)

    find = commands.add_parser("find", help="pages of a document containing some text")
    find.add_argument("document")
    find.add_argument("text")
    find.set_defaults(func=cmd_find)

    page = commands.add_parser("page", help="print the extracted text of one page")
    page.add_argument("document")
    page.add_argument("number", type=int)
    page.set_defaults(func=cmd_page)

    commands.add_parser("audit-text", help="pages whose text layer probably omits visible text").set_defaults(
        func=cmd_audit_text
    )
    commands.add_parser(
        "scaffold-instruments", help="create minimal instrument records for ISINs listed in breach reports"
    ).set_defaults(func=cmd_scaffold_instruments)

    as_of_help = "use only what was shown public by this date (YYYY-MM-DD)"
    availability_help = (
        "which availability dates --as-of trusts: 'estimated' (publisher or server dates, the default) or "
        "'observed' (only the day the project retrieved each file, so nothing counts too early)"
    )
    modes = [mode.value for mode in AvailabilityMode]
    status = commands.add_parser("status", help="derived breach-disclosure status per ISIN and period")
    status.add_argument("--as-of", type=date.fromisoformat, help=as_of_help)
    status.add_argument(
        "--availability", choices=modes, default=AvailabilityMode.ESTIMATED.value, help=availability_help
    )
    status.set_defaults(func=cmd_status)

    build = commands.add_parser("build", help="write CSV exports (and optionally SQLite)")
    build.add_argument("--out", type=Path, default=Path("exports"))
    build.add_argument("--sqlite", type=Path, help="also write a SQLite database to this path")
    build.set_defaults(func=cmd_build)

    report = commands.add_parser("report", help="observability report in Markdown")
    report.add_argument("--out", type=Path)
    report.set_defaults(func=cmd_report)

    schema = commands.add_parser("schema", help="write JSON Schemas for the record types")
    schema.add_argument("--out", type=Path, default=Path("schema"))
    schema.set_defaults(func=cmd_schema)

    show = commands.add_parser("show", help="everything recorded about one ISIN")
    show.add_argument("isin")
    show.add_argument("--as-of", type=date.fromisoformat, help=as_of_help)
    show.add_argument("--availability", choices=modes, default=AvailabilityMode.ESTIMATED.value, help=availability_help)
    show.set_defaults(func=cmd_show)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
