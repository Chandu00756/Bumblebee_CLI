"""Bumblebee CLI — diff two NDJSON scan results, show new / fixed findings."""
from __future__ import annotations
import json
from pathlib import Path
from rich.table import Table
from rich import box
from bbcli.theme import console

_SEV_COLOR = {
    "critical": "red", "high": "orange3",
    "medium": "yellow", "low": "cyan", "info": "dim",
}


def _load_findings(ndjson_path: str) -> dict[str, dict]:
    """Return findings keyed by  'ecosystem:name@version'."""
    out: dict[str, dict] = {}
    path = Path(ndjson_path)
    if not path.exists():
        console.print(f"  [danger]File not found:[/danger] {ndjson_path}")
        return out
    with open(path) as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if rec.get("record_type") == "finding":
                key = (
                    f"{rec.get('ecosystem','?')}:"
                    f"{rec.get('package_name','?')}@{rec.get('package_version','?')}"
                )
                out[key] = rec
    return out


def diff_scans(before_path: str, after_path: str) -> None:
    """Print a Rich diff table comparing two scan NDJSON files."""
    before = _load_findings(before_path)
    after  = _load_findings(after_path)

    new_keys   = set(after)  - set(before)
    fixed_keys = set(before) - set(after)
    same_keys  = set(after)  & set(before)

    console.print(
        f"\n  [bold yellow]Scan Diff[/bold yellow]  "
        f"[dim]{Path(before_path).name}[/dim] [muted]→[/muted] [dim]{Path(after_path).name}[/dim]\n"
    )

    if new_keys:
        t = Table(
            title=f"[red]🔴 New Findings ({len(new_keys)})[/red]",
            box=box.SIMPLE, show_header=True, header_style="bold red",
        )
        t.add_column("Package",   style="bold white")
        t.add_column("Severity",  min_width=10)
        t.add_column("Ecosystem", min_width=10)
        t.add_column("Advisory",  style="dim")
        for k in sorted(new_keys):
            rec = after[k]
            sev = rec.get("severity", "info").lower()
            c   = _SEV_COLOR.get(sev, "white")
            t.add_row(
                f"{rec.get('package_name')}@{rec.get('package_version','')}",
                f"[{c}]{sev.upper()}[/{c}]",
                rec.get("ecosystem", "?"),
                rec.get("advisory_id", rec.get("catalog_name", "?")),
            )
        console.print(t)

    if fixed_keys:
        t = Table(
            title=f"[green]✅ Fixed / Resolved ({len(fixed_keys)})[/green]",
            box=box.SIMPLE, show_header=True, header_style="bold green",
        )
        t.add_column("Package",   style="bold white")
        t.add_column("Severity",  min_width=10)
        t.add_column("Ecosystem", min_width=10)
        for k in sorted(fixed_keys):
            rec = before[k]
            sev = rec.get("severity", "info").lower()
            c   = _SEV_COLOR.get(sev, "white")
            t.add_row(
                f"{rec.get('package_name')}@{rec.get('package_version','')}",
                f"[{c}]{sev.upper()}[/{c}]",
                rec.get("ecosystem", "?"),
            )
        console.print(t)

    if not new_keys and not fixed_keys:
        console.print("  [green]No changes between scans.[/green]\n")
    else:
        console.print(
            f"\n  [dim]Summary:[/dim] "
            f"[red]+{len(new_keys)} new[/red]  "
            f"[green]-{len(fixed_keys)} fixed[/green]  "
            f"[dim]{len(same_keys)} unchanged[/dim]\n"
        )
