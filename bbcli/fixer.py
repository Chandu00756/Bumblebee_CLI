"""Bumblebee CLI — generate (or apply) fix commands for vulnerable packages."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from typing import Optional
from rich.table import Table
from rich import box
from bbcli.theme import console

_SEV_COLOR = {
    "critical": "red", "high": "orange3",
    "medium": "yellow", "low": "cyan", "info": "dim",
}

# (package, fixed_version) → upgrade shell command
_FIX_CMD: dict[str, object] = {
    "npm":      lambda p, v: f"npm install {p}@{v}" if v else f"npm audit fix",
    "pypi":     lambda p, v: f"pip install --upgrade \"{p}=={v}\"" if v else f"pip install --upgrade {p}",
    "go":       lambda p, v: f"go get {p}@v{v}" if v else f"go get -u {p}",
    "rubygems": lambda p, v: f"gem update {p}" + (f" --version {v}" if v else ""),
    "cargo":    lambda p, v: f"cargo update -p {p}" + (f" --precise {v}" if v else ""),
    "maven":    lambda p, v: f"# Update {p} to {v} in pom.xml" if v else f"# Check {p} in pom.xml",
}


def generate_fixes(ndjson_path: str, apply: bool = False) -> int:
    """
    Show (and optionally apply) fix commands for findings in a scan file.
    Returns the number of findings.
    """
    findings: list[dict] = []
    path = Path(ndjson_path)
    if not path.exists():
        console.print(f"  [danger]File not found:[/danger] {ndjson_path}")
        return 0

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
                findings.append(rec)

    if not findings:
        console.print("  [green]No findings — nothing to fix.[/green]")
        return 0

    t = Table(
        title=f"🔧 Fix Commands  ({len(findings)} finding{'s' if len(findings) != 1 else ''})",
        box=box.SIMPLE, show_header=True, header_style="bold yellow",
    )
    t.add_column("Package",      style="bold white", min_width=24)
    t.add_column("Severity",     min_width=10)
    t.add_column("Fix command",  style="bold cyan")

    cmds: list[str] = []
    for rec in findings:
        eco  = rec.get("ecosystem", "?")
        name = rec.get("package_name", "?")
        ver  = (
            rec.get("fixed_version")
            or rec.get("safe_version")
            or rec.get("patched_versions", "").split(",")[0].strip().lstrip(">=")
            or ""
        )
        sev   = rec.get("severity", "info").lower()
        color = _SEV_COLOR.get(sev, "white")
        fn    = _FIX_CMD.get(eco)
        cmd   = fn(name, ver) if callable(fn) else f"# Update {name} manually"
        cmds.append(cmd)
        t.add_row(
            f"{name}@{rec.get('package_version', '')}",
            f"[{color}]{sev.upper()}[/{color}]",
            cmd,
        )

    console.print(t)

    if apply:
        console.print("\n  [bold yellow]Applying fixes…[/bold yellow]\n")
        for cmd in cmds:
            if cmd.startswith("#"):
                console.print(f"  [dim]{cmd}[/dim]")
                continue
            console.print(f"  [cyan]$ {cmd}[/cyan]")
            result = subprocess.run(
                cmd, shell=False, capture_output=True, text=True,  # noqa: S603
                args=cmd.split()
            )
            if result.returncode == 0:
                console.print("  [green]OK[/green]")
            else:
                console.print(f"  [red]Failed:[/red] {result.stderr.strip()[:200]}")
    else:
        console.print(
            "\n  [dim]Showing fix commands only. "
            "Run [bold]bee fix --apply[/bold] to execute them.[/dim]\n"
        )

    return len(findings)
