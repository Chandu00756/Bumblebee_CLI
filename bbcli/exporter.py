"""Export scan findings to SARIF 2.1, CSV, or JSON formats.

- SARIF: integrates with GitHub Advanced Security / VS Code SARIF viewer
- CSV:   spreadsheet-friendly, one row per finding
- JSON:  clean normalized array of findings
"""
from __future__ import annotations
import csv
import json
import uuid
from datetime import datetime
from pathlib import Path
from rich.table import Table
from rich import box
from bbcli.theme import console

_REPORTS_DIR = Path.home() / ".bumblebee-cli" / "reports"


def _load_findings(ndjson_path: str) -> list[dict]:
    findings = []
    try:
        for line in Path(ndjson_path).read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("record_type") == "finding":
                findings.append(rec)
    except FileNotFoundError:
        console.print(f"[danger]File not found:[/danger] {ndjson_path}")
    return findings


def _sev_to_sarif(sev: str) -> str:
    m = {"critical": "error", "high": "error", "medium": "warning",
         "low": "note", "info": "none"}
    return m.get((sev or "info").lower(), "warning")


def export_sarif(ndjson_path: str, output: str | None = None) -> str:
    """Export findings as SARIF 2.1 JSON (for GitHub Security tab)."""
    from bbcli import __version__
    findings = _load_findings(ndjson_path)

    results = []
    rules   = {}
    for f in findings:
        rule_id = f.get("catalog_name") or f.get("cve_id") or "BEE-001"
        pkg     = f.get("package_name", "unknown")
        ver     = f.get("package_version", "")
        eco     = f.get("ecosystem", "")
        sev     = (f.get("severity") or "info").lower()
        desc    = f.get("description") or f.get("summary") or f"Vulnerable package: {pkg}@{ver}"

        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "name": rule_id.replace("-", "").replace("_", ""),
                "shortDescription": {"text": f"{rule_id}: {pkg}"},
                "fullDescription":  {"text": desc},
                "defaultConfiguration": {"level": _sev_to_sarif(sev)},
                "properties": {"tags": [eco, sev]},
            }

        results.append({
            "ruleId":  rule_id,
            "level":   _sev_to_sarif(sev),
            "message": {"text": f"{pkg}@{ver} ({eco}) — {desc}"},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": "package-lock.json", "uriBaseId": "%SRCROOT%"},
                    "region": {"startLine": 1},
                }
            }],
            "properties": {
                "package":   pkg,
                "version":   ver,
                "ecosystem": eco,
                "severity":  sev,
            },
        })

    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name":            "bumblebee-cli",
                    "version":         __version__,
                    "informationUri":  "https://pypi.org/project/bumblebee-cli/",
                    "rules":           list(rules.values()),
                }
            },
            "results": results,
            "columnKind": "utf16CodeUnits",
        }],
    }

    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(output) if output else _REPORTS_DIR / f"scan_{ts}.sarif.json"
    path.write_text(json.dumps(sarif, indent=2))
    console.print(f"  [success]SARIF 2.1:[/success] {path}  ({len(findings)} findings)")
    return str(path)


def export_csv(ndjson_path: str, output: str | None = None) -> str:
    """Export findings as CSV."""
    findings = _load_findings(ndjson_path)

    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(output) if output else _REPORTS_DIR / f"scan_{ts}.csv"

    fields = ["package_name", "package_version", "ecosystem", "severity",
              "catalog_name", "cve_id", "description", "fix_version"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for f in findings:
            writer.writerow({k: f.get(k, "") for k in fields})

    console.print(f"  [success]CSV:[/success] {path}  ({len(findings)} rows)")
    return str(path)


def export_json(ndjson_path: str, output: str | None = None) -> str:
    """Export findings as clean JSON array."""
    findings = _load_findings(ndjson_path)

    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(output) if output else _REPORTS_DIR / f"scan_{ts}.findings.json"

    # Normalize — keep only relevant fields
    normalized = []
    for f in findings:
        normalized.append({
            "package":     f.get("package_name", ""),
            "version":     f.get("package_version", ""),
            "ecosystem":   f.get("ecosystem", ""),
            "severity":    (f.get("severity") or "info").lower(),
            "advisory":    f.get("catalog_name") or f.get("cve_id") or "",
            "description": f.get("description") or f.get("summary") or "",
            "fix_version": f.get("fix_version") or "",
        })

    path.write_text(json.dumps(normalized, indent=2))
    console.print(f"  [success]JSON:[/success] {path}  ({len(findings)} findings)")
    return str(path)


def export_all(ndjson_path: str, output_dir: str | None = None) -> None:
    """Export to all three formats at once."""
    console.print(f"  [muted]Exporting:[/muted] [accent]{Path(ndjson_path).name}[/accent]\n")

    base = Path(output_dir) if output_dir else _REPORTS_DIR
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    export_sarif(ndjson_path, str(base / f"scan_{ts}.sarif.json"))
    export_csv(ndjson_path,   str(base / f"scan_{ts}.csv"))
    export_json(ndjson_path,  str(base / f"scan_{ts}.findings.json"))
