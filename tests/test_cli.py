from __future__ import annotations

import json

import pytest

from bc3param.cli import main
from tests.test_generate import SNIPPET


@pytest.fixture
def bc3(tmp_path):
    p = tmp_path / "mini.bc3"
    p.write_bytes(SNIPPET.encode("cp1252"))
    return p


def test_validate_ok(bc3, capsys):
    assert main(["validate", str(bc3)]) == 0
    out = capsys.readouterr().out
    assert "3 families" in out and "0 errors" in out


def test_validate_reports_errors(tmp_path, capsys):
    p = tmp_path / "bad.bc3"
    p.write_text("~V|||\n~P|BAD001$|\\A\\a\\\n%M(2,2)=1,2\\|\n", encoding="cp1252")
    assert main(["validate", str(p)]) == 1
    out = capsys.readouterr().out
    assert "BAD001$ line 2" in out and "1 errors" in out


def test_inspect(bc3, capsys):
    assert main(["inspect", str(bc3), "OEB020$"]) == 0
    out = capsys.readouterr().out
    assert "A  Nº TUBOS" in out and "1: ' 2 '" in out and "Nocturno" in out
    assert "combinations: 4" in out


def test_resolve_derived_and_selection(bc3, capsys):
    assert main(["resolve", str(bc3), "OEB020ab"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["code"] == "OEB020ab" and d["price"] == 8.31
    assert main(["resolve", str(bc3), "OEB020$", "-s", "1,2"]) == 0
    assert json.loads(capsys.readouterr().out)["code"] == "OEB020ab"


def test_resolve_unknown_code_fails(bc3, capsys):
    assert main(["resolve", str(bc3), "ZZZ999ab"]) == 1
    assert "error" in capsys.readouterr().err


def test_generate_jsonl_and_json(bc3, tmp_path, capsys):
    out = tmp_path / "items.jsonl"
    assert main(["generate", str(bc3), "--chapter", "OEB#", "--out", str(out)]) == 0
    lines = out.read_text(encoding="utf-8").splitlines()
    assert [json.loads(l)["code"] for l in lines] == ["OEB020aa", "OEB020ab", "OEB020ba", "OEB030a"]
    assert "4 items" in capsys.readouterr().err
    out2 = tmp_path / "items.json"
    assert main(["generate", str(bc3), "--family", "OEB020$", "--format", "json", "--include-invalid",
                 "--no-decomposition", "--limit", "2", "--out", str(out2)]) == 0
    data = json.loads(out2.read_text(encoding="utf-8"))
    assert [x["code"] for x in data] == ["OEB020aa", "OEB020ab"] and data[0]["decomposition"] == []


def test_generate_range_to_stdout(bc3, capsys):
    assert main(["generate", str(bc3), "--range", "OEC000..OEC999"]) == 0
    assert json.loads(capsys.readouterr().out.strip())["code"] == "OEC010a"
