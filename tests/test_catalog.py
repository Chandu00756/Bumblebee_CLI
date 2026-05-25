import pytest, json, tempfile
from pathlib import Path
from unittest.mock import patch
from bbcli import catalog

def _make_catalog(entries=None):
    return {
        "schema_version": "0.1.0",
        "entries": entries or [{
            "id": "test-001", "name": "Test Advisory",
            "ecosystem": "npm", "package": "evil-pkg",
            "versions": ["1.0.0"], "severity": "critical"
        }]
    }

def test_validate_catalog_valid():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(_make_catalog(), f)
        path = f.name
    assert catalog.validate_catalog(path) is True

def test_validate_catalog_missing_field():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        data = _make_catalog()
        del data["entries"][0]["severity"]
        json.dump(data, f)
        path = f.name
    assert catalog.validate_catalog(path) is False

def test_create_catalog():
    with patch.object(catalog, "CATALOG_DIR", Path(tempfile.mkdtemp())):
        path = catalog.create_catalog("test-cat", _make_catalog()["entries"])
        assert Path(path).exists()
        data = json.loads(Path(path).read_text())
        assert data["schema_version"] == "0.1.0"
        assert len(data["entries"]) == 1