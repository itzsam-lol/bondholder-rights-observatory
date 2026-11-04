# Contributing

Corrections matter more than volume. If a record misreads its source, please open an issue with the document and page.

## Adding records

1. Read [docs/methods.md](docs/methods.md) and [docs/source-policy.md](docs/source-policy.md).
2. Register any new publisher in `data/sources.yaml`, after reading its terms and robots.txt.
3. Add the file with `brdo add-document`, or with `--from-file` for manual-only sources.
4. Write the record, reviewing the file's rendered pages as well as its text.
5. Run the checks:

```console
$ uv run brdo validate
$ uv run brdo verify
$ uv run brdo build
$ uv run brdo report --out docs/observability-report.md
$ uv run brdo schema
$ uv run pytest
```

## Ground rules

- Say who said it. Records are attributed statements, not facts about a company.
- Never turn absence into a finding. Log the search and let the status say `no_report_found`.
- Keep disagreements. Add a discrepancy rather than choosing a side.
- For a compliance statement, record who made it (the issuer or its auditor) and what it says it covers, as printed.
- Never overwrite. A revised file is a new document, and an amended clause is a new provision with `amends`.
- Do not work around a block, a login or a challenge. Record the limit instead.
- Do not commit source documents, and do not record natural persons.
- Log searches that fail as well as those that succeed.
