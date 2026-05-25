"""Bumblebee CLI — parse package manifests / lockfiles without the scanner binary."""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Iterator
from rich.table import Table
from rich import box
from bbcli.theme import console

# (ecosystem, filename) pairs we know how to parse
_PARSERS: dict[str, str] = {
    "package.json":           "npm",
    "package-lock.json":      "npm",
    "requirements.txt":       "pypi",
    "requirements-dev.txt":   "pypi",
    "requirements-test.txt":  "pypi",
    "requirements-prod.txt":  "pypi",
    "Pipfile":                "pypi",
    "go.mod":                 "go",
    "Gemfile":                "rubygems",
    "Cargo.toml":             "cargo",
}


# ── per-format parsers ────────────────────────────────────────────────────────

def _parse_package_json(path: Path) -> Iterator[tuple[str, str, str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return
    for section in (
        "dependencies", "devDependencies",
        "peerDependencies", "optionalDependencies",
    ):
        for name, ver in (data.get(section) or {}).items():
            yield "npm", name, re.sub(r"^[^0-9]*", "", str(ver))


def _parse_requirements(path: Path) -> Iterator[tuple[str, str, str]]:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-", "git+", "http")):
            continue
        m = re.match(r"^([\w\-\.]+)\s*[=~><!]+\s*([^\s;#,\[]+)", line)
        if m:
            yield "pypi", m.group(1), m.group(2)
        elif re.match(r"^[\w\-\.]+$", line):
            yield "pypi", line, ""


def _parse_go_mod(path: Path) -> Iterator[tuple[str, str, str]]:
    in_require = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_require = True
            continue
        if in_require and stripped == ")":
            in_require = False
            continue
        if in_require or stripped.startswith("require "):
            m = re.match(r"^\s*([\w\.\-/]+)\s+v([\w\.\-]+)", stripped)
            if m:
                yield "go", m.group(1), m.group(2)


def _parse_gemfile(path: Path) -> Iterator[tuple[str, str, str]]:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(
            r"""^\s*gem\s+['"]([^'"]+)['"](?:,\s*['"]([^'"]+)['"])?""", line
        )
        if m:
            yield "rubygems", m.group(1), m.group(2) or ""


def _parse_cargo_toml(path: Path) -> Iterator[tuple[str, str, str]]:
    content = path.read_text(encoding="utf-8", errors="replace")
    # Match lines like:  serde = "1.0"  or  serde = { version = "1.0" }
    for m in re.finditer(
        r'^([a-zA-Z0-9_\-]+)\s*=\s*(?:"([^"]+)"|.*?version\s*=\s*"([^"]+)")',
        content,
        re.MULTILINE,
    ):
        name = m.group(1)
        ver  = m.group(2) or m.group(3) or ""
        if name in {
            "name", "version", "edition", "authors", "description",
            "license", "repository", "homepage", "documentation", "readme",
        }:
            continue
        yield "cargo", name, ver.lstrip("^~=<>")


_PARSER_FNS = {
    "npm":      {"package.json": _parse_package_json,
                 "package-lock.json": _parse_package_json},
    "pypi":     {"requirements.txt": _parse_requirements,
                 "requirements-dev.txt": _parse_requirements,
                 "requirements-test.txt": _parse_requirements,
                 "requirements-prod.txt": _parse_requirements,
                 "Pipfile": _parse_requirements},
    "go":       {"go.mod": _parse_go_mod},
    "rubygems": {"Gemfile": _parse_gemfile},
    "cargo":    {"Cargo.toml": _parse_cargo_toml},
}


# ── public API ────────────────────────────────────────────────────────────────

def scan_lockfiles(root: str) -> list[tuple[str, str, str]]:
    """Return [(ecosystem, package, version)] from all manifests under root."""
    root_path = Path(root).expanduser().resolve()
    packages: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()

    for eco, fns in _PARSER_FNS.items():
        for fname, parser in fns.items():
            for match in root_path.rglob(fname):
                # Skip node_modules / .venv / vendor trees
                if any(p in match.parts for p in (
                    "node_modules", ".venv", "venv", "vendor", ".git",
                    "__pycache__", "dist", "build",
                )):
                    continue
                try:
                    for _, name, ver in parser(match):
                        key = (eco, name)
                        if key not in seen:
                            seen.add(key)
                            packages.append((eco, name, ver))
                except Exception:
                    continue

    return packages


def show_lockfile_deps(root: str) -> None:
    """Print a Rich table of all dependencies found in manifests under root."""
    packages = scan_lockfiles(root)
    if not packages:
        console.print("  [muted]No manifests found under:[/muted] " + root)
        return

    t = Table(
        title=f"📦 Dependencies — {root}",
        box=box.SIMPLE, show_header=True, header_style="bold yellow",
    )
    t.add_column("Ecosystem", style="bold cyan", min_width=12)
    t.add_column("Package",   style="bold white")
    t.add_column("Version",   style="dim")

    eco_colors = {
        "npm": "bold yellow", "pypi": "bold blue",
        "go": "bold cyan", "rubygems": "bold red", "cargo": "bold magenta",
    }

    eco_counts: dict[str, int] = {}
    for eco, name, ver in sorted(packages, key=lambda x: (x[0], x[1])):
        c = eco_colors.get(eco, "white")
        t.add_row(f"[{c}]{eco}[/{c}]", name, ver or "any")
        eco_counts[eco] = eco_counts.get(eco, 0) + 1

    console.print(t)
    eco_summary = "  ".join(f"[bold]{eco}[/bold]: {n}" for eco, n in sorted(eco_counts.items()))
    console.print(
        f"\n  [dim]Total:[/dim] [accent]{len(packages)}[/accent] dependencies  |  {eco_summary}\n"
    )
