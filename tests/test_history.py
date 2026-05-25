import pytest, json, tempfile
from pathlib import Path
from unittest.mock import patch
from bbcli import history

def test_add_and_retrieve():
    with tempfile.TemporaryDirectory() as td:
        fake_history = Path(td) / "history.json"
        with patch.object(history, "HISTORY_FILE", fake_history):
            history.add_entry("baseline", "/tmp/scan.ndjson",
                              {"files_considered": 500, "records": 100}, 0)
            last = history.get_last_scan()
            assert last is not None
            assert last["profile"] == "baseline"
            assert last["findings"] == 0
            assert last["status"] == "clean"

def test_findings_status():
    with tempfile.TemporaryDirectory() as td:
        fake_history = Path(td) / "history.json"
        with patch.object(history, "HISTORY_FILE", fake_history):
            history.add_entry("deep", "/tmp/scan.ndjson", {}, 3)
            last = history.get_last_scan()
            assert last["status"] == "findings"

def test_clear_history():
    with tempfile.TemporaryDirectory() as td:
        fake_history = Path(td) / "history.json"
        with patch.object(history, "HISTORY_FILE", fake_history):
            history.add_entry("baseline", "/tmp/s.ndjson", {}, 0)
            history.clear_history()
            assert history.get_last_scan() is None