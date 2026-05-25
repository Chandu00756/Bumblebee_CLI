"""Policy-as-code enforcement via .bee-policy.yml

Policy file format (YAML):
  max_severity: high          # fail if any finding at this level or above
  max_findings: 0             # fail if total findings exceed this
  block_ecosystems:           # fail if any dep from these ecosystems
    - npm
  require_license_allow:      # fail if any dep license NOT in this list
    - MIT
    - Apache-2.0
  block_packages:             # fail unconditionally if these packages present
    - lodash
    - left-pad@1.0.0
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from rich.table import Table
from rich import box
from bbcli.theme import console

_SEVERITY_ORDER = ["info", "low", "medium", "high", "critical"]

# Default policy (audit-only, never blocks)
_DEFAULTS = {
    "max_severity":          "none",   # none = never block on severity
    "max_findings":          -1,       # -1 = unlimited
    "block_ecosystems":      [],
    "require_license_allow": [],
    "block_packages":        [],
}


def _load_policy(policy_path: str | None) -> dict:
    """Load .bee-policy.yml from explicit path or auto-discover."""
    search_paths = []
    if policy_path:
        search_paths = [Path(policy_path)]
    else:
        search_paths = [
            Path.cwd() / ".bee-policy.yml",
            Path.cwd() / ".bee-policy.yaml",
            Path.home() / ".bumblebee-cli" / "policy.yml",
        ]

    for p in search_paths:
        if p.exists():
            try:
                # Try PyYAML first, fall back to simple key:value parser
                try:
                    import yaml  # type: ignore
                    raw = yaml.safe_load(p.read_text()) or {}
                except ImportError:
                    raw = _simple_yaml_parse(p.read_text())
                policy = {**_DEFAULTS, **raw}
                return policy, str(p)
            except Exception:
                pass

    return _DEFAULTS.copy(), None


def _simple_yaml_parse(text: str) -> dict:
    """Minimal YAML parser for flat key:value and simple lists."""
    result: dict = {}
    current_list_key = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_list_key:
            result[current_list_key].append(stripped[2:].strip())
            continue
        if ":" in stripped:
            k, _, v = stripped.partition(":")
            k = k.strip()
            v = v.strip()
            if v == "" or v == "[]":
                result[k] = [] if v == "[]" else None
                current_list_key = k if v == "" else None
                if v == "" and k not in result:
                    result[k] = []
            else:
                current_list_key = None
                # Try numeric
                try:
                    result[k] = int(v)
                except ValueError:
                    result[k] = v
    return result


def _load_findings(ndjson_path: str) -> tuple[list[dict], list[dict]]:
    findings, packages = [], []
    try:
        for line in Path(ndjson_path).read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            rt = rec.get("record_type")
            if rt == "finding":
                findings.append(rec)
            elif rt == "package":
                packages.append(rec)
    except FileNotFoundError:
        pass
    return findings, packages


def _sev_index(sev: str) -> int:
    return _SEVERITY_ORDER.index(sev.lower()) if sev.lower() in _SEVERITY_ORDER else 0


def enforce_policy(ndjson_path: str, policy_path: str | None = None) -> int:
    """Evaluate findings against policy. Returns exit code (0=pass, 1=fail)."""
    from bbcli import __version__
    console.print(f"[primary]🐝 Bumblebee CLI[/primary] [muted]v{__version__} — Dependency security scanner for macOS[/muted]")

    policy, loaded_from = _load_policy(policy_path)
    findings, packages  = _load_findings(ndjson_path)

    if loaded_from:
        console.print(f"  [muted]Policy:[/muted] [accent]{loaded_from}[/accent]")
    else:
        console.print("  [muted]Policy: (defaults — no .bee-policy.yml found)[/muted]")

    violations: list[str] = []

    # Rule 1: max_severity
    max_sev = (policy.get("max_severity") or "none").lower()
    if max_sev != "none" and max_sev in _SEVERITY_ORDER:
        threshold_idx = _sev_index(max_sev)
        for f in findings:
            f_sev = (f.get("severity") or "info").lower()
            if _sev_index(f_sev) >= threshold_idx:
                violations.append(
                    f"[danger]SEVERITY[/danger] {f.get('package_name')}@{f.get('package_version','')} "
                    f"has [{f_sev}]{f_sev.upper()}[/{f_sev}] severity (threshold: {max_sev.upper()})"
                )

    # Rule 2: max_findings
    max_findings = policy.get("max_findings", -1)
    if max_findings >= 0 and len(findings) > max_findings:
        violations.append(
            f"[danger]FINDINGS[/danger] {len(findings)} findings exceed limit of {max_findings}"
        )

    # Rule 3: block_ecosystems
    blocked_eco = [e.lower() for e in (policy.get("block_ecosystems") or [])]
    if blocked_eco:
        for pkg in packages:
            eco = (pkg.get("ecosystem") or "").lower()
            if eco in blocked_eco:
                violations.append(
                    f"[danger]ECOSYSTEM[/danger] {pkg.get('package_name')} uses blocked ecosystem: {eco}"
                )

    # Rule 4: block_packages
    blocked_pkgs = [p.lower() for p in (policy.get("block_packages") or [])]
    if blocked_pkgs:
        for pkg in packages + findings:
            name = (pkg.get("package_name") or "").lower()
            ver  = pkg.get("package_version", "")
            if name in blocked_pkgs or f"{name}@{ver}".lower() in blocked_pkgs:
                violations.append(
                    f"[danger]BLOCKED[/danger] Package {name}@{ver} is explicitly blocked by policy"
                )

    # Results table
    t = Table(title="📋 Policy Check Results", box=box.DOUBLE_EDGE,
              title_style="primary", header_style="accent")
    t.add_column("Rule",      style="bold", width=16)
    t.add_column("Setting")
    t.add_column("Result")

    def _pass(v): return f"[success]✅ {v}[/success]"
    def _fail(v): return f"[danger]❌ {v}[/danger]"
    def _skip(v): return f"[muted]{v}[/muted]"

    t.add_row("max_severity",
              str(policy.get("max_severity","none")),
              _pass("OK") if max_sev == "none" or not any("SEVERITY" in v for v in violations)
              else _fail("VIOLATED"))

    t.add_row("max_findings",
              str(max_findings) if max_findings >= 0 else "unlimited",
              _pass(f"{len(findings)} findings") if not any("FINDINGS" in v for v in violations)
              else _fail(f"{len(findings)} exceed {max_findings}"))

    t.add_row("block_ecosystems",
              ", ".join(blocked_eco) if blocked_eco else "none",
              _pass("OK") if not any("ECOSYSTEM" in v for v in violations)
              else _fail("blocked eco found"))

    t.add_row("block_packages",
              f"{len(blocked_pkgs)} rules" if blocked_pkgs else "none",
              _pass("OK") if not any("BLOCKED" in v for v in violations)
              else _fail("blocked pkg found"))

    console.print(t)

    if violations:
        console.print(f"\n  [danger]❌ Policy FAILED — {len(violations)} violation(s):[/danger]")
        for v in violations:
            console.print(f"    • {v}")
        return 1
    else:
        console.print("\n  [success]✅ Policy PASSED — all rules satisfied.[/success]")
        return 0
