"""Interactive .beeignore manager — add, list, remove rules."""
from __future__ import annotations
from pathlib import Path
from rich.table import Table
from rich import box
from bbcli.theme import console

_COMMENT_HEADER = """\
# .beeignore — Bumblebee CLI suppress list
# Format (one rule per line):
#   package               — suppress any version of this package
#   package@version       — suppress exact version
#   ecosystem:package     — suppress across one ecosystem
#   ecosystem:package@ver — suppress exact version in ecosystem
#   # comment lines are ignored
"""


def _find_beeignore(root: str | None = None) -> Path:
    """Return path to .beeignore in root (or cwd if None)."""
    base = Path(root) if root else Path.cwd()
    return base / ".beeignore"


def _load_rules(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(errors="replace").splitlines()
    return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]


def _write(path: Path, rules: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_header = ""
    if path.exists():
        content = path.read_text(errors="replace")
        header_lines = [l for l in content.splitlines() if l.startswith("#") or l == ""]
        existing_header = "\n".join(header_lines).strip()

    header = existing_header if existing_header else _COMMENT_HEADER.strip()
    path.write_text(header + "\n" + "\n".join(sorted(set(rules))) + "\n")


def list_rules(root: str | None = None) -> None:
    from bbcli import __version__
    console.print(f"[primary]🐝 Bumblebee CLI[/primary] [muted]v{__version__} — Dependency security scanner for macOS[/muted]")

    path  = _find_beeignore(root)
    rules = _load_rules(path)

    if not rules:
        console.print(f"  [muted]No .beeignore rules found.[/muted]  (looked in [accent]{path}[/accent])")
        console.print("  Use [accent]bee ignore add <package>[/accent] to add rules.")
        return

    t = Table(title=f"🙈 .beeignore  ({path})", box=box.SIMPLE,
              title_style="primary", header_style="accent")
    t.add_column("#",      width=4, justify="right")
    t.add_column("Rule",   style="accent")
    t.add_column("Type")

    for i, rule in enumerate(sorted(rules), 1):
        if ":" in rule and "@" in rule:
            rtype = "ecosystem + version"
        elif ":" in rule:
            rtype = "ecosystem"
        elif "@" in rule:
            rtype = "package + version"
        else:
            rtype = "package name"
        t.add_row(str(i), rule, rtype)

    console.print(t)
    console.print(f"  [muted]{len(rules)} rule(s) — file:[/muted] [accent]{path}[/accent]")


def add_rule(rule: str, root: str | None = None) -> None:
    from bbcli import __version__
    console.print(f"[primary]🐝 Bumblebee CLI[/primary] [muted]v{__version__} — Dependency security scanner for macOS[/muted]")

    path  = _find_beeignore(root)
    rules = _load_rules(path)
    rule  = rule.strip().lower()

    if rule in rules:
        console.print(f"  [warning]Already exists:[/warning] [accent]{rule}[/accent]")
        return

    rules.append(rule)
    _write(path, rules)
    console.print(f"  [success]✅ Added:[/success] [accent]{rule}[/accent]  →  {path}")


def remove_rule(rule: str, root: str | None = None) -> None:
    from bbcli import __version__
    console.print(f"[primary]🐝 Bumblebee CLI[/primary] [muted]v{__version__} — Dependency security scanner for macOS[/muted]")

    path  = _find_beeignore(root)
    rules = _load_rules(path)
    rule  = rule.strip().lower()

    if rule not in rules:
        console.print(f"  [warning]Rule not found:[/warning] [accent]{rule}[/accent]")
        list_rules(root)
        return

    rules.remove(rule)
    _write(path, rules)
    console.print(f"  [success]✅ Removed:[/success] [accent]{rule}[/accent]")


def clear_rules(root: str | None = None) -> None:
    from bbcli import __version__
    console.print(f"[primary]🐝 Bumblebee CLI[/primary] [muted]v{__version__} — Dependency security scanner for macOS[/muted]")

    path = _find_beeignore(root)
    if path.exists():
        path.unlink()
        console.print(f"  [success]✅ Cleared:[/success] {path}")
    else:
        console.print("  [muted]No .beeignore file to clear.[/muted]")
