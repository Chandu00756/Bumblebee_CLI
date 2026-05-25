import pytest, json, tempfile
from pathlib import Path
from bbcli import reporter

SAMPLE_NDJSON = "\n".join([
    json.dumps({"record_type": "package", "ecosystem": "npm",
                "package_name": "lodash", "version": "4.17.21",
                "confidence": "high", "source_file": "/code/package-lock.json"}),
    json.dumps({"record_type": "scan_summary", "files_considered": 100,
                "records": 1, "findings": 0, "duplicates": 0}),
])

def test_generate_html():
    with tempfile.TemporaryDirectory() as td:
        ndjson_path = Path(td) / "scan.ndjson"
        ndjson_path.write_text(SAMPLE_NDJSON)
        out = reporter.generate_html(str(ndjson_path))
        assert Path(out).exists()
        content = Path(out).read_text()
        assert "Bumblebee CLI" in content
        assert "lodash" in content

def test_generate_html_with_findings():
    ndjson_with_finding = SAMPLE_NDJSON + "\n" + json.dumps({
        "record_type": "finding", "severity": "critical",
        "package_name": "evil-pkg", "version": "1.0.0",
        "ecosystem": "npm", "catalog_name": "Test Advisory",
        "evidence": "exact match"
    })
    with tempfile.TemporaryDirectory() as td:
        ndjson_path = Path(td) / "scan.ndjson"
        ndjson_path.write_text(ndjson_with_finding)
        out = reporter.generate_html(str(ndjson_path))
        content = Path(out).read_text()
        assert "evil-pkg" in content
        assert "CRITICAL" in content