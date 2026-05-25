"""Bumblebee CLI — filesystem watcher that auto-scans on manifest changes."""
from __future__ import annotations
import time
from pathlib import Path
from bbcli.theme import console

# Files whose modification triggers an automatic re-scan
WATCHED_NAMES = {
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
    "Pipfile", "Pipfile.lock", "pyproject.toml", "poetry.lock",
    "go.mod", "go.sum",
    "Gemfile", "Gemfile.lock",
    "Cargo.toml", "Cargo.lock",
    "pom.xml", "build.gradle", "build.gradle.kts",
}

# Directories to skip
_SKIP_DIRS = {
    "node_modules", ".venv", "venv", "vendor", ".git",
    "__pycache__", "dist", "build", ".tox",
}


def _snapshot(root: Path) -> dict[str, float]:
    """Return {filepath: mtime} for all watched manifest files under root."""
    snap: dict[str, float] = {}
    for fname in WATCHED_NAMES:
        for match in root.rglob(fname):
            if any(part in _SKIP_DIRS for part in match.parts):
                continue
            try:
                snap[str(match)] = match.stat().st_mtime
            except OSError:
                pass
    return snap


def watch_and_scan(
    root: str,
    profile: str = "baseline",
    on_change=None,
    poll_interval: float = 2.0,
) -> None:
    """
    Poll root every poll_interval seconds.
    When a manifest changes, call on_change(root_str, profile) if provided.
    Runs until Ctrl-C.
    """
    root_path = Path(root).expanduser().resolve()
    console.print(
        f"\n  [bold yellow]👁  Watching[/bold yellow] [accent]{root_path}[/accent]  "
        f"[dim](profile: {profile})[/dim]"
    )
    console.print(
        "  [dim]Triggers on: package.json, requirements.txt, go.mod, "
        "Cargo.toml, Gemfile, pom.xml, and more.[/dim]"
    )
    console.print("  [dim]Press Ctrl+C to stop.[/dim]\n")

    last = _snapshot(root_path)

    try:
        while True:
            time.sleep(poll_interval)
            current = _snapshot(root_path)

            changed = [
                p for p, mt in current.items() if last.get(p) != mt
            ] + [p for p in current if p not in last]

            if changed:
                for p in changed:
                    console.print(
                        f"  [bold yellow]Changed:[/bold yellow] [accent]{Path(p).name}[/accent]"
                    )
                console.print(
                    f"  [bold green]Triggering scan of[/bold green] "
                    f"[accent]{root_path}[/accent]…\n"
                )
                if on_change:
                    on_change(str(root_path), profile)
                last = current

    except KeyboardInterrupt:
        console.print("\n  [dim]Watcher stopped.[/dim]\n")
