import pytest
import yaml

from brdo.cli import main
from tests.conftest import text_stream, write_pdf


def _write_minimal_data(root):
    root.mkdir()
    (root / "sources.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "id": "exchange",
                    "name": "Exchange",
                    "kind": "exchange",
                    "domains": ["exchange.example"],
                    "retrieval": "manual_only",
                    "redistribution": "link_only",
                    "excerpts": "short_quotation",
                },
                {
                    "id": "closed",
                    "name": "Closed",
                    "kind": "exchange",
                    "domains": ["closed.example"],
                    "retrieval": "excluded",
                    "redistribution": "no_links",
                    "excerpts": "none",
                },
            ]
        ),
        encoding="utf-8",
    )
    (root / "documents.yaml").write_text("# Every file the dataset cites.\n", encoding="utf-8")


def _run(data, cache, *arguments) -> int:
    return main(["--data", str(data), "--cache", str(cache), *arguments])


def test_a_file_downloaded_in_a_browser_can_be_ingested_from_a_manual_only_source(tmp_path, capsys):
    data, cache = tmp_path / "data", tmp_path / "cache"
    _write_minimal_data(data)
    pdf = write_pdf(tmp_path / "kid.pdf", [text_stream("Financial Covenants on page one")])
    url = "https://bond.exchange.example/kid.pdf"
    code = _run(
        data,
        cache,
        "add-document",
        url,
        "--id",
        "kid",
        "--type",
        "key_information_document",
        "--title",
        "KID",
        "--from-file",
        str(pdf),
    )
    assert code == 0
    record = yaml.safe_load((data / "documents.yaml").read_text())[0]
    assert record["retrieved_manually"] is True
    assert record["media_type"] == "application/pdf" and record["pages"] == 1
    assert _run(data, cache, "validate") == 0
    assert _run(data, cache, "find", "kid", "financial covenants") == 0
    assert "p1:" in capsys.readouterr().out


def test_the_pipeline_will_not_fetch_from_a_manual_only_source(tmp_path, capsys):
    data, cache = tmp_path / "data", tmp_path / "cache"
    _write_minimal_data(data)
    code = _run(
        data,
        cache,
        "add-document",
        "https://bond.exchange.example/kid.pdf",
        "--id",
        "kid",
        "--type",
        "key_information_document",
        "--title",
        "KID",
    )
    assert code == 1
    assert "retrieval policy" in capsys.readouterr().err
    assert not yaml.safe_load((data / "documents.yaml").read_text())


def test_even_a_manual_file_is_refused_from_an_excluded_source(tmp_path, capsys):
    data, cache = tmp_path / "data", tmp_path / "cache"
    _write_minimal_data(data)
    pdf = write_pdf(tmp_path / "x.pdf", [text_stream("text")])
    code = _run(
        data,
        cache,
        "add-document",
        "https://closed.example/x.pdf",
        "--id",
        "x",
        "--type",
        "other",
        "--title",
        "X",
        "--from-file",
        str(pdf),
    )
    assert code == 1
    assert "excluded" in capsys.readouterr().err


def test_validate_fails_on_an_invalid_record(tmp_path, capsys):
    data = tmp_path / "data"
    _write_minimal_data(data)
    (data / "issuers.yaml").write_text(yaml.safe_dump([{"id": "x"}]), encoding="utf-8")
    with pytest.raises(SystemExit) as caught:
        _run(data, tmp_path / "cache", "validate")
    assert caught.value.code == 1
    assert "issuers.yaml[0] name" in capsys.readouterr().err


def test_show_reports_an_unknown_isin(tmp_path, capsys):
    data = tmp_path / "data"
    _write_minimal_data(data)
    assert _run(data, tmp_path / "cache", "show", "INE501X07588") == 1
    assert "no record" in capsys.readouterr().err
