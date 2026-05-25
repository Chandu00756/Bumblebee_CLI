"""Core scan runner wrapping the bumblebee binary."""
import subprocess, shutil, json, os, tempfile, time
from pathlib import Path
from typing import Optional


# ── .beeignore support ────────────────────────────────────────────────────────

def _load_beeignore(root: str | None = None) -> set[str]:
    """
    Load ignore rules from .beeignore in root or cwd.
    Each line: 'package', 'package@version', or 'ecosystem:package'.
    Lines starting with # are comments.
    """
    search_dirs = []
    if root:
        search_dirs.append(Path(root))
    search_dirs.append(Path.cwd())
    search_dirs.append(Path.home() / ".bumblebee-cli")

    rules: set[str] = set()
    for d in search_dirs:
        ignore_file = d / ".beeignore"
        if ignore_file.exists():
            for line in ignore_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    rules.add(line.lower())
            break  # use first .beeignore found
    return rules


def _is_ignored(finding: dict, rules: set[str]) -> bool:
    """Return True if this finding matches any .beeignore rule."""
    if not rules:
        return False
    name = (finding.get("package_name") or "").lower()
    ver  = (finding.get("package_version") or "").lower()
    eco  = (finding.get("ecosystem") or "").lower()
    return (
        name in rules
        or f"{name}@{ver}" in rules
        or f"{eco}:{name}" in rules
        or f"{eco}:{name}@{ver}" in rules
    )
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich import box
from bbcli.theme import console, ECOSYSTEM_COLORS, SEVERITY_STYLES

def _bb() -> str:
    p = shutil.which("bumblebee")
    if p:
        return p
    gobin = os.environ.get("GOBIN") or os.path.join(os.path.expanduser("~"), "go", "bin")
    candidate = os.path.join(gobin, "bumblebee")
    if os.path.isfile(candidate):
        return candidate
    raise FileNotFoundError("Bumblebee not found. Run: bbcli install")

def run_scan(profile, roots, ecosystems, exposure_catalog,
             findings_only, max_duration, output_file,
             quiet=False, dry_run=False) -> dict:
    cmd = [_bb(), "scan", "--profile", profile]
    for r in roots:
        cmd += ["--root", r]
    for e in ecosystems:
        cmd += ["--ecosystem", e]
    if exposure_catalog:
        cmd += ["--exposure-catalog", exposure_catalog]
    if findings_only and exposure_catalog:
        cmd.append("--findings-only")
    if max_duration:
        cmd += ["--max-duration", max_duration]
    if dry_run:
        from rich.panel import Panel
        from rich import box
        console.print(Panel(
            f"[accent]Command:[/accent] {' '.join(cmd)}",
            title="[info]🔍 Dry Run[/info]", box=box.ROUNDED
        ))
        return {}
    if not quiet:
        console.print(f"\n[primary]🐝 Starting {profile.upper()} scan…[/primary]")

    # Load ignore rules from first .beeignore found in roots or cwd
    ignore_rules = _load_beeignore(roots[0] if roots else None)
    if ignore_rules:
        console.print(f"  [dim].beeignore: {len(ignore_rules)} rule(s) active[/dim]")

    records, findings, diagnostics, summary = [], [], [], {}
    stdout_lines = []
    ignored_count = 0
    start = time.time()
    with Progress(
        SpinnerColumn(spinner_name="dots12", style="primary"),
        TextColumn("[accent]{task.description}[/accent]"),
        BarColumn(bar_width=38, style="primary", complete_style="success"),
        TextColumn("[muted]{task.fields[stats]}[/muted]"),
        TimeElapsedColumn(),
        console=console, transient=True,
    ) as prog:
        task = prog.add_task(f"Scanning ({profile})…", total=None, stats="")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            stdout_lines.append(line)
            try:
                rec = json.loads(line)
                rt  = rec.get("record_type", "")
                if rt == "package":
                    records.append(rec)
                    prog.update(task, stats=f"pkgs={len(records)}")
                elif rt == "finding":
                    if _is_ignored(rec, ignore_rules):
                        ignored_count += 1
                    else:
                        findings.append(rec)
                    prog.update(task, stats=f"pkgs={len(records)} [danger]findings={len(findings)}[/danger]")
                elif rt == "scan_summary":
                    summary = rec
                elif rt == "diagnostic":
                    diagnostics.append(rec)
            except json.JSONDecodeError:
                pass
        proc.wait()
    Path(output_file).write_text("\n".join(stdout_lines) + "\n")
    if ignored_count:
        console.print(f"  [dim].beeignore suppressed {ignored_count} finding(s)[/dim]")
    return {
        "records": records, "findings": findings,
        "diagnostics": diagnostics, "summary": summary,
        "output_file": output_file,
        "elapsed": time.time() - start,
        "returncode": proc.returncode,
    }

def show_scan_results(result: dict, verbose: bool = False):
    records  = result.get("records", [])
    findings = result.get("findings", [])
    summary  = result.get("summary", {})
    elapsed  = result.get("elapsed", 0)
    status   = "[success]✅ CLEAN[/success]" if not findings else f"[danger]⚠️  {len(findings)} FINDING(S)[/danger]"
    console.print()
    console.print(Panel(
        f"[muted]Files scanned:[/muted]  [accent]{summary.get('files_considered', len(records)):,}[/accent]\n"
        f"[muted]Packages:[/muted]       [accent]{len(records):,}[/accent]\n"
        f"[muted]Findings:[/muted]       {status}\n"
        f"[muted]Duplicates:[/muted]     [accent]{summary.get('duplicates', 0)}[/accent]\n"
        f"[muted]Duration:[/muted]       [accent]{elapsed:.2f}s[/accent]",
        title="[primary]📊 Scan Summary[/primary]", box=box.DOUBLE_EDGE, style="primary"
    ))
    # Ecosystem breakdown
    if records:
        eco_counts: dict[str, int] = {}
        for r in records:
            eco = r.get("ecosystem", "unknown")
            eco_counts[eco] = eco_counts.get(eco, 0) + 1
        t = Table(title="📦 Ecosystem Breakdown", box=box.SIMPLE_HEAVY,
                  title_style="primary", header_style="accent")
        t.add_column("Ecosystem", style="bold white")
        t.add_column("Packages",  justify="right")
        t.add_column("Bar",       no_wrap=True)
        max_c = max(eco_counts.values())
        for eco, cnt in sorted(eco_counts.items(), key=lambda x: -x[1]):
            bar = "█" * int(cnt/max_c*24) + "░" * (24 - int(cnt/max_c*24))
            sty = ECOSYSTEM_COLORS.get(eco, "white")
            t.add_row(f"[{sty}]{eco}[/{sty}]", str(cnt), f"[{sty}]{bar}[/{sty}]")
        console.print(t)
    # Findings
    if findings:
        ft = Table(title="🚨 Security Findings", box=box.HEAVY_HEAD,
                   title_style="danger", header_style="bold white", show_lines=True)
        ft.add_column("Severity", width=10)
        ft.add_column("Package",  style="bold white")
        ft.add_column("Version",  style="accent")
        ft.add_column("Ecosystem", width=14)
        ft.add_column("Advisory", style="info")
        ft.add_column("Evidence", style="muted")
        for f in findings:
            sev = f.get("severity", "info").lower()
            sty = SEVERITY_STYLES.get(sev, "white")
            eco = f.get("ecosystem", "")
            ft.add_row(
                f"[{sty}]{sev.upper()}[/{sty}]",
                f.get("package_name", ""), f.get("version", ""),
                f"[{ECOSYSTEM_COLORS.get(eco,'white')}]{eco}[/{ECOSYSTEM_COLORS.get(eco,'white')}]",
                f.get("catalog_name", f.get("catalog_id", "")),
                f.get("evidence", ""),
            )
        console.print(ft)
    else:
        console.print("[success]✅ No findings — your machine looks clean![/success]")
    if verbose and records:
        pt = Table(title="📋 All Packages (first 500)", box=box.MINIMAL,
                   title_style="info", header_style="accent")
        pt.add_column("Ecosystem", width=14)
        pt.add_column("Package",   style="bold white")
        pt.add_column("Version",   style="accent")
        pt.add_column("Confidence",width=10)
        pt.add_column("Source",    style="muted")
        for r in records[:500]:
            eco  = r.get("ecosystem", "")
            conf = r.get("confidence", "")
            csty = {"high": "success", "medium": "warning", "low": "danger"}.get(conf, "white")
            pt.add_row(
                f"[{ECOSYSTEM_COLORS.get(eco,'white')}]{eco}[/{ECOSYSTEM_COLORS.get(eco,'white')}]",
                r.get("package_name", ""), r.get("version", ""),
                f"[{csty}]{conf}[/{csty}]",
                Path(r.get("source_file","")).name,
            )
        console.print(pt)
    console.print(f"\n[muted]📁 NDJSON:[/muted] [accent]{result['output_file']}[/accent]")

def run_roots(profile: str, roots: list):
    cmd = [_bb(), "roots", "--profile", profile]
    for r in roots:
        cmd += ["--root", r]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    t = Table(title=f"🗂  Scan Roots — {profile}", box=box.SIMPLE_HEAVY,
              title_style="primary", header_style="accent")
    t.add_column("Root Kind", style="accent")
    t.add_column("Path",      style="white")
    for line in result.stdout.strip().splitlines():
        if "\t" in line:
            kind, path = line.split("\t", 1)
        else:
            kind, path = "root", line
        t.add_row(f"[muted]{kind}[/muted]", f"{'✅' if os.path.exists(path) else '❌'} {path}")
    console.print(t)

def run_selftest() -> bool:
    r = subprocess.run([_bb(), "selftest"], capture_output=True, text=True, timeout=30)
    if r.returncode == 0:
        console.print(f"[success]✅ Selftest passed:[/success] [accent]{r.stdout.strip()}[/accent]")
        return True
    console.print(f"[danger]❌ Selftest failed:[/danger] {r.stderr.strip()}")
    return False