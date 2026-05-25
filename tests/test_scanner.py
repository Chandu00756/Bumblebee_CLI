import pytest, json, os, tempfile
from unittest.mock import patch, MagicMock
from bbcli import scanner

MOCK_PACKAGE = json.dumps({
    "record_type": "package", "ecosystem": "npm",
    "package_name": "lodash", "version": "4.17.21",
    "confidence": "high", "source_file": "/code/package-lock.json"
})
MOCK_FINDING = json.dumps({
    "record_type": "finding", "severity": "critical",
    "package_name": "evil-pkg", "version": "1.0.0",
    "ecosystem": "npm", "catalog_name": "Test Advisory",
    "evidence": "exact match"
})
MOCK_SUMMARY = json.dumps({
    "record_type": "scan_summary", "files_considered": 1000,
    "records": 1, "findings": 0, "duplicates": 5
})

def test_run_scan_dry_run():
    with patch("bbcli.scanner._bb", return_value="/bin/bumblebee"):
        result = scanner.run_scan(
            "baseline", [], [], None, False, None,
            "/tmp/test.ndjson", dry_run=True
        )
        assert result == {}

def test_show_scan_results_clean(capsys):
    result = {
        "records": [json.loads(MOCK_PACKAGE)],
        "findings": [],
        "summary": {"files_considered": 1000, "records": 1, "duplicates": 0},
        "output_file": "/tmp/test.ndjson",
        "elapsed": 1.23,
    }
    # Should not raise
    scanner.show_scan_results(result)

def test_show_scan_results_with_findings():
    result = {
        "records": [],
        "findings": [json.loads(MOCK_FINDING)],
        "summary": {},
        "output_file": "/tmp/test.ndjson",
        "elapsed": 0.5,
    }
    scanner.show_scan_results(result)