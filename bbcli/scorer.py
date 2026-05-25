"""Security score calculator — produces an A–F grade from scan findings."""
from __future__ import annotations
import json
from pathlib import Path
from rich.table import Table
from rich.panel import Panel
from rich import box
from bbcli.theme import console

# Severity weights (deductions per finding)
_WEIGHTS = {
    "critical": 25,
    "high":     15,
    "medium":    7,
    "low":       2,
    "info":      0,
}

# Grade thresholds
def _grade(score: int) -> tuple[str, str]:
    if score >= 90: return "A", "success"
    if score >= 75: return "B", "accent"
    if score >= 60: return "C", "warning"
    if score >= 40: return "D", "danger"
    return "F", "danger"


def _load_findings(ndjson_path: str) -> list[dict]:
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
            if rec.get("record_type") == "finding":
                findings.append(rec)
            elif rec.get("record_type") == "package":
                packages.append(rec)
    except FileNotFoundError:
        pass
    return findings, packages


def compute_score(ndjson_path: str) -> dict:
    """Return score dict: score (0-100), grade, counts per severity."""
    findings, packages = _load_findings(ndjson_path)
    counts: dict[str, int] = {}
    deduction = 0
    for f in findings:
        sev = (f.get("severity") or "info").lower()
        counts[sev] = counts.get(sev, 0) + 1
        deduction += _WEIGHTS.get(sev, 0)

    # Cap deduction at 100
    score = max(0, 100 - deduction)
    grade, color = _grade(score)
    return {
        "score":      score,
        "grade":      grade,
        "color":      color,
        "counts":     counts,
        "findings":   len(findings),
        "packages":   len(packages),
        "deduction":  deduction,
    }


def show_score(ndjson_path: str) -> None:
    """Print a rich security score dashboard."""
    from bbcli import __version__
    console.print(f"[primary]🐝 Bumblebee CLI[/primary] [muted]v{__version__} — Dependency security scanner for macOS[/muted]")

    result = compute_score(ndjson_path)
    score  = result["score"]
    grade  = result["grade"]
    color  = result["color"]
    counts = result["counts"]

    # Score panel
    bar_filled = int(score / 5)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)
    console.print(Panel(
        f"[{color}]  {grade}  [/{color}]  [{color}]{score}/100[/{color}]\n\n"
        f"  [{color}]{bar}[/{color}]  [{color}]{score}%[/{color}]",
        title="🔐 Security Score",
        border_style=color,
        padding=(1, 4),
        expand=False,
    ))

    # Breakdown table
    t = Table(box=box.SIMPLE, show_header=True, header_style="accent",
              title="Finding Breakdown", title_style="primary")
    t.add_column("Severity",   style="bold")
    t.add_column("Count",      justify="right")
    t.add_column("Deduction",  justify="right", style="danger")

    severity_order = ["critical", "high", "medium", "low", "info"]
    sev_styles = {
        "critical": "critical", "high": "high",
        "medium": "medium",     "low": "low", "info": "muted",
    }
    total_deducted = 0
    for sev in severity_order:
        cnt = counts.get(sev, 0)
        if cnt == 0:
            continue
        ded = _WEIGHTS.get(sev, 0) * cnt
        total_deducted += ded
        t.add_row(
            f"[{sev_styles[sev]}]{sev.upper()}[/{sev_styles[sev]}]",
            str(cnt), f"-{ded}"
        )

    if not counts:
        t.add_row("[success]No findings[/success]", "0", "0")
    else:
        t.add_row("[bold]TOTAL[/bold]", str(result["findings"]), f"-{total_deducted}")

    console.print(t)
    console.print(
        f"  Packages scanned: [accent]{result['packages']}[/accent]  |  "
        f"Grade: [{color}]{grade}[/{color}]  |  "
        f"Score: [{color}]{score}/100[/{color}]"
    )

    # Advice
    if grade == "A":
        console.print("\n  [success]✅ Excellent posture — no action needed.[/success]")
    elif grade == "B":
        console.print("\n  [accent]🔷 Good — consider fixing medium findings.[/accent]")
    elif grade == "C":
        console.print("\n  [warning]⚠️  Fair — high severity issues need attention.[/warning]")
    else:
        console.print("\n  [danger]🚨 Poor — critical/high findings must be remediated.[/danger]")
