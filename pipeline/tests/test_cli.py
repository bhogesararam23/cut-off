from pathlib import Path

from cutoff.__main__ import main

CONFIG = str(Path(__file__).resolve().parents[1] / "config.example.json")


def test_mock_then_check(tmp_path, capsys):
    out = tmp_path / "out"
    assert main(["mock", "--config", CONFIG, "--out", str(out)]) == 0
    assert main(["check", "--config", CONFIG, "--out", str(out)]) == 0
    assert "follow the data format" in capsys.readouterr().out


def test_check_reports_problems(tmp_path, capsys):
    (tmp_path / "event.json").write_text("{}", encoding="utf-8")
    assert main(["check", "--config", CONFIG, "--out", str(tmp_path)]) == 1
    assert "problem" in capsys.readouterr().out
