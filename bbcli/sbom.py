"""Bumblebee CLI — SBOM export in SPDX-2.3 or CycloneDX-1.5 JSON format."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from bbcli.theme import console


def _load_packages(ndjson_path: str) -> list[dict]:
    packages: list[dict] = []
    with open(ndjson_path) as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if rec.get("record_type") == "package":
                packages.append(rec)
    return packages


def _purl(eco: str, name: str, ver: str) -> str:
    return f"pkg:{eco}/{name}@{ver}" if ver else f"pkg:{eco}/{name}"


def export_spdx(ndjson_path: str, output: Optional[str] = None) -> str:
    """Generate SPDX 2.3 JSON SBOM from a scan NDJSON file."""
    packages = _load_packages(ndjson_path)
    now = datetime.now(timezone.utc).isoformat()
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")

    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "bumblebee-scan-sbom",
        "documentNamespace": f"https://bumblebee-cli.dev/sbom/{ts}",
        "creationInfo": {
            "created": now,
            "creators": ["Tool: bumblebee-cli-2.0.0"],
        },
        "packages": [
            {
                "SPDXID": f"SPDXRef-pkg-{i}",
                "name": pkg.get("package_name", "unknown"),
                "versionInfo": pkg.get("package_version", ""),
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": _purl(
                            pkg.get("ecosystem", "generic"),
                            pkg.get("package_name", "?"),
                            pkg.get("package_version", ""),
                        ),
                    }
                ],
            }
            for i, pkg in enumerate(packages)
        ],
    }

    out_dir = Path.home() / ".bumblebee-cli" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = output or str(out_dir / f"sbom_{ts}.spdx.json")
    with open(out, "w") as fh:
        json.dump(sbom, fh, indent=2)

    console.print(
        f"  [green]SPDX 2.3 SBOM:[/green] [accent]{out}[/accent]  "
        f"[dim]({len(packages)} packages)[/dim]"
    )
    return out


def export_cyclonedx(ndjson_path: str, output: Optional[str] = None) -> str:
    """Generate CycloneDX 1.5 JSON SBOM from a scan NDJSON file."""
    packages = _load_packages(ndjson_path)
    now = datetime.now(timezone.utc).isoformat()
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")

    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{ts}",
        "version": 1,
        "metadata": {
            "timestamp": now,
            "tools": [{"vendor": "Bumblebee", "name": "bumblebee-cli", "version": "2.0.0"}],
        },
        "components": [
            {
                "type": "library",
                "name": pkg.get("package_name", "unknown"),
                "version": pkg.get("package_version", ""),
                "purl": _purl(
                    pkg.get("ecosystem", "generic"),
                    pkg.get("package_name", "?"),
                    pkg.get("package_version", ""),
                ),
            }
            for pkg in packages
        ],
    }

    out_dir = Path.home() / ".bumblebee-cli" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = output or str(out_dir / f"sbom_{ts}.cdx.json")
    with open(out, "w") as fh:
        json.dump(sbom, fh, indent=2)

    console.print(
        f"  [green]CycloneDX 1.5 SBOM:[/green] [accent]{out}[/accent]  "
        f"[dim]({len(packages)} packages)[/dim]"
    )
    return out
