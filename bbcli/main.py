"""Bumblebee CLI — full Typer entry point."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import typer
from rich.panel import Panel
from rich import box
from bbcli.theme import console, BANNER, MINI_BANNER
from bbcli import installer, scanner, scheduler, reporter, history, catalog
from bbcli.interactive import run_interactive

app          = typer.Typer(name="bee", add_completion=True,
                           rich_markup_mode="rich", no_args_is_help=False,
                           help="🐝 Bumblebee CLI — Supply-chain security scanner for macOS")
schedule_app = typer.Typer(help="Manage scheduled scans via macOS launchd")
catalog_app  = typer.Typer(help="Manage exposure catalogs")
history_app  = typer.Typer(help="View scan history")
report_app   = typer.Typer(help="Generate HTML / PDF reports")
app.add_typer(schedule_app, name="schedule")
app.add_typer(catalog_app,  name="catalog")
app.add_typer(history_app,  name="history")
app.add_typer(report_app,   name="report")

def _repl() -> None:
    """
    Persistent REPL shell.
    Type `bee` with no arguments to enter it.
    Commands are the same as CLI subcommands but without the `bee` prefix.
    """
    import shlex
    try:
        import readline  # noqa: F401  — enables up/down arrow history on macOS
    except ImportError:
        pass

    from rich.prompt import Prompt
    from rich.table import Table

    console.print(BANNER)
    console.print(
        "\n  [dim]Type a command and press Enter.  "
        "[bold]help[/bold] lists commands.  "
        "[bold]exit[/bold] quits.[/dim]\n"
    )

    while True:
        try:
            line = Prompt.ask("  [bold yellow]\U0001f41d[/bold yellow] ").strip()
        except KeyboardInterrupt:
            console.print("\n  [dim]Type [bold]exit[/bold] to quit.[/dim]")
            continue
        except EOFError:
            break

        if not line:
            continue

        if line.lower() in ("exit", "quit", "q", "bye"):
            console.print("\n  [dim]Goodbye. Stay secure.[/dim]\n")
            break

        if line.lower() in ("help", "?", "h"):
            tbl = Table(box=box.SIMPLE, show_header=True, header_style="bold yellow")
            tbl.add_column("Command", style="bold cyan", min_width=28)
            tbl.add_column("What it does", style="white")
            rows = [
                ("scan PATH [--profile PROF]",     "Scan a directory for supply-chain threats"),
                ("quick [PATH]",                   "Fast baseline scan of current directory"),
                ("threat-scan [PATH]",             "Deep scan against all threat intel advisories"),
                ("roots [PATH]",                   "Preview what will be scanned (dry run)"),
                ("install",                        "Install the Bumblebee scanner binary"),
                ("update",                         "Update Bumblebee to latest version"),
                ("status",                         "Show installation and version info"),
                ("selftest",                       "Run built-in scanner selftest"),
                ("report html FILE.ndjson",        "Generate an HTML security report"),
                ("report pdf  FILE.ndjson",        "Generate a PDF security report"),
                ("report last --format html",      "Report from the most recent scan"),
                ("schedule setup",                  "Wizard — pick a preset scan scenario"),
                ("schedule add NAME --when TIME",    "Add a custom scheduled scan"),
                ("schedule list",                    "List all scheduled scans"),
                ("schedule enable/disable NAME",     "Toggle a schedule on or off"),
                ("schedule logs NAME",               "Tail log for a scheduled scan"),
                ("schedule run NAME",                "Run a schedule immediately"),
                ("schedule remove NAME",             "Delete a scheduled scan"),
                ("catalog list",                     "List exposure catalogs"),
                ("catalog create NAME",              "Create a new catalog"),
                ("catalog fetch-intel",              "Download all threat intel catalogs"),
                ("catalog list-intel",               "Show available threat intel sources"),
                ("history",                          "Show scan history"),
                ("history clear",                    "Clear scan history"),
                ("exit",                             "Quit the shell"),
            ]
            for cmd, desc in rows:
                tbl.add_row(cmd, desc)
            console.print(tbl)
            continue

        try:
            args = shlex.split(line)
            try:
                app(args, standalone_mode=True)
            except SystemExit:
                pass
        except ValueError as exc:
            console.print(f"  [red]Parse error:[/red] {exc}")
        except Exception as exc:
            console.print(f"  [red]Error:[/red] {exc}")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """🐝 No arguments? Opens the interactive REPL shell."""
    if ctx.invoked_subcommand is None:
        _repl()

# ── install / update / uninstall / status / selftest / version ───────────────

@app.command()
def install(update: bool = typer.Option(False,"--update","-u")):
    """⬇️  Install (or update) Bumblebee via go install."""
    console.print(MINI_BANNER); installer.install(update=update)

@app.command()
def update():
    """🔄 Update Bumblebee to latest."""
    console.print(MINI_BANNER); installer.install(update=True)

@app.command()
def status():
    """⚙️  Show installation status."""
    from bbcli.interactive import _do_status; _do_status()

@app.command()
def selftest():
    """✅ Run Bumblebee built-in selftest."""
    scanner.run_selftest()

@app.command()
def version():
    """ℹ️  Show CLI and binary versions."""
    from bbcli import __version__
    console.print(f"[primary]🐝 Bumblebee CLI[/primary] [accent]v{__version__}[/accent]")
    console.print(f"[muted]Binary:[/muted] [accent]{installer.get_version()}[/accent]")

# ── report prompt (shown after every scan) ───────────────────────────────────

def _prompt_report(ndjson_path: str) -> None:
    """Ask the user if they want a report after a scan completes."""
    import subprocess
    from rich.prompt import Prompt
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    downloads = Path.home() / "Downloads"
    downloads.mkdir(exist_ok=True)
    try:
        choice = Prompt.ask(
            "\n  Generate a report?",
            choices=["html", "pdf", "both", "no"],
            default="no",
        )
    except (KeyboardInterrupt, EOFError):
        return
    if choice in ("html", "both"):
        out = str(downloads / f"bumblebee-report-{ts}.html")
        path = reporter.generate_html(ndjson_path, output=out)
        if path:
            subprocess.run(["open", path], check=False)
    if choice in ("pdf", "both"):
        out = str(downloads / f"bumblebee-report-{ts}.pdf")
        path = reporter.generate_pdf(ndjson_path, output=out)
        if path:
            subprocess.run(["open", path], check=False)

# ── scan ──────────────────────────────────────────────────────────────────────

@app.command()
def scan(
    path:             Optional[str]  = typer.Argument(None),
    profile:          str            = typer.Option("baseline","--profile","-p"),
    root:             List[str]      = typer.Option([],"--root","-r"),
    ecosystem:        List[str]      = typer.Option([],"--ecosystem","-e"),
    exposure_catalog: Optional[str]  = typer.Option(None,"--catalog","-c"),
    findings_only:    bool           = typer.Option(False,"--findings-only"),
    max_duration:     Optional[str]  = typer.Option(None,"--max-duration"),
    output:           Optional[str]  = typer.Option(None,"--output","-o"),
    verbose:          bool           = typer.Option(False,"--verbose","-v"),
    dry_run:          bool           = typer.Option(False,"--dry-run"),
):
    """Run a Bumblebee scan.

    Pass an optional path to scan a specific folder:
      scan                         # whole machine
      scan ~/projects/myapp        # specific folder
      scan . --profile deep        # current dir, deep profile
      scan --root ~/code -e npm    # flag style still works
    """
    console.print(MINI_BANNER)
    roots_list = list(root)
    if path:
        roots_list = [str(Path(path).expanduser().resolve())] + roots_list
    cat_path = exposure_catalog
    if cat_path and not os.path.exists(cat_path):
        candidate = catalog.CATALOG_DIR / f"{cat_path}.json"
        if candidate.exists(): cat_path = str(candidate)
    out_dir  = Path.home() / ".bumblebee-cli" / "scans"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = output or str(out_dir / f"scan_{profile}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ndjson")
    result   = scanner.run_scan(profile, roots_list, list(ecosystem), cat_path,
                                findings_only, max_duration, out_file, dry_run=dry_run)
    if result and not dry_run:
        scanner.show_scan_results(result, verbose=verbose)
        history.add_entry(profile, out_file, result.get("summary",{}), len(result.get("findings",[])))
        _prompt_report(out_file)

@app.command()
def quick(
    path: Optional[str] = typer.Argument(None),
):
    """One-command quick baseline scan. Optionally pass a folder path."""
    console.print(MINI_BANNER)
    roots_list = [str(Path(path).expanduser().resolve())] if path else []
    out_dir  = Path.home() / ".bumblebee-cli" / "scans"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = str(out_dir / f"quick_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ndjson")
    result   = scanner.run_scan("baseline", roots_list, [], None, False, None, out_file)
    if result:
        scanner.show_scan_results(result)
        history.add_entry("baseline", out_file, result.get("summary",{}), len(result.get("findings",[])))
        _prompt_report(out_file)

@app.command("threat-scan")
def threat_scan(
    catalog_name: str       = typer.Argument("trapdoor-crypto-stealer"),
    path:         Optional[str] = typer.Option(None,"--path","-d",help="Folder to scan (default: home)"),
    root:         List[str] = typer.Option([],"--root","-r"),
    max_duration: str       = typer.Option("10m","--max-duration"),
):
    """Deep scan against known threat intel advisories."""
    console.print(MINI_BANNER)
    cat_path = catalog.CATALOG_DIR / f"{catalog_name}.json"
    if not cat_path.exists():
        res = catalog.fetch_threat_intel(catalog_name)
        if not res: raise typer.Exit(1)
    roots_list = list(root)
    if path:
        roots_list = [str(Path(path).expanduser().resolve())] + roots_list
    if not roots_list:
        roots_list = [str(Path.home())]
    out_dir  = Path.home() / ".bumblebee-cli" / "scans"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = str(out_dir / f"threat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ndjson")
    result   = scanner.run_scan("deep", roots_list, [], str(cat_path), True, max_duration, out_file)
    if result:
        scanner.show_scan_results(result)
        history.add_entry("deep", out_file, result.get("summary",{}), len(result.get("findings",[])))
        _prompt_report(out_file)

@app.command()
def roots(
    profile: str       = typer.Option("baseline","--profile","-p"),
    root:    List[str] = typer.Option([],"--root","-r"),
):
    """🗂  Preview what will be scanned (no actual scan)."""
    console.print(MINI_BANNER); scanner.run_roots(profile, list(root))

# ── schedule ──────────────────────────────────────────────────────────────────

@schedule_app.command("add")
def schedule_add(
    name:             str            = typer.Argument(...),
    profile:          str            = typer.Option("baseline","--profile","-p"),
    root:             List[str]      = typer.Option([],"--root","-r"),
    ecosystem:        List[str]      = typer.Option([],"--ecosystem","-e"),
    when:             str            = typer.Option("daily","--when","-w"),
    exposure_catalog: Optional[str]  = typer.Option(None,"--catalog","-c"),
    findings_only:    bool           = typer.Option(False,"--findings-only"),
    output_dir:       str            = typer.Option(str(Path.home()/".bumblebee-cli"/"scans"),"--output-dir"),
):
    """📅 Add a scheduled scan (daily | morning | evening | hourly | weekly | monthly | HH:MM)."""
    scheduler.add_schedule(name, profile, list(root), list(ecosystem),
                           exposure_catalog, findings_only, when, output_dir)

@schedule_app.command("list")
def schedule_list():
    """📋 List all scheduled scans."""
    scheduler.show_schedules()

@schedule_app.command("remove")
def schedule_remove(name: str = typer.Argument(...)):
    """🗑  Remove a scheduled scan."""
    scheduler.remove_schedule(name)

@schedule_app.command("run")
def schedule_run(name: str = typer.Argument(...)):
    """Run a scheduled scan right now."""
    scheduler.run_now(name)

@schedule_app.command("enable")
def schedule_enable(name: str = typer.Argument(...)):
    """Enable a disabled scheduled scan."""
    scheduler.enable_schedule(name)

@schedule_app.command("disable")
def schedule_disable(name: str = typer.Argument(...)):
    """Disable a scheduled scan without deleting it."""
    scheduler.disable_schedule(name)

@schedule_app.command("logs")
def schedule_logs(name: str = typer.Argument(...),
                  lines: int = typer.Option(50, "--lines", "-n")):
    """Tail the log output of a scheduled scan."""
    scheduler.show_logs(name, lines)

@schedule_app.command("setup")
def schedule_setup():
    """Interactive wizard — pick a preset scheduling scenario."""
    from rich.prompt import Prompt
    console.print(MINI_BANNER)

    scenarios = {
        "1": ("Full machine scan (daily at 9 AM)",
               "full-machine", "baseline", [str(Path.home())], "daily"),
        "2": ("Scan a specific folder (daily at 9 AM)",
               None, "baseline", None, "daily"),
        "3": ("Project deep scan — npm/pypi only (morning)",
               None, "deep", None, "morning"),
        "4": ("Threat intel watch — matches known malicious packages (hourly)",
               "threat-watch", "deep", [str(Path.home())], "hourly"),
        "5": ("Weekly full scan every Monday",
               "weekly-full", "baseline", [str(Path.home())], "weekly"),
        "6": ("Nightly deep scan at midnight",
               None, "deep", [str(Path.home())], "00:00"),
    }

    console.print("\n  [bold yellow]Scheduling scenarios:[/bold yellow]\n")
    for k, (label, *_) in scenarios.items():
        console.print(f"  [bold cyan]{k}[/bold cyan]  {label}")
    console.print()

    choice = Prompt.ask("  Pick a scenario", choices=list(scenarios.keys()))
    label, default_name, profile, default_roots, when = scenarios[choice]

    if default_name:
        name = Prompt.ask("  Schedule name", default=default_name)
    else:
        name = Prompt.ask("  Schedule name")

    if default_roots is None:
        folder = Prompt.ask("  Folder to scan", default=str(Path.home()))
        roots_list = [folder]
    else:
        roots_list = default_roots

    eco_input = Prompt.ask("  Ecosystems (comma-sep, or blank for all)", default="")
    ecosystems = [e.strip() for e in eco_input.split(",") if e.strip()]

    catalog_name = None
    if choice == "4":
        catalog_name = "trapdoor-crypto-stealer"

    scheduler.add_schedule(
        name, profile, roots_list, ecosystems,
        catalog_name, choice == "4", when,
        str(Path.home() / ".bumblebee-cli" / "scans"),
    )
    console.print(f"\n  [bold green]Schedule '[bold white]{name}[/bold white]' created.[/bold green]")
    console.print(f"  [dim]View all schedules:[/dim] [bold]schedule list[/bold]")

# ── report ────────────────────────────────────────────────────────────────────

@report_app.command("html")
def report_html(ndjson: str = typer.Argument(...),
                output: Optional[str] = typer.Option(None,"--output","-o"),
                open_:  bool = typer.Option(False,"--open")):
    """📄 Generate HTML report from NDJSON."""
    rpt = reporter.generate_html(ndjson, output)
    if open_: import subprocess; subprocess.run(["open", rpt])

@report_app.command("pdf")
def report_pdf(ndjson: str = typer.Argument(...),
               output: Optional[str] = typer.Option(None,"--output","-o"),
               open_:  bool = typer.Option(False,"--open")):
    """📄 Generate PDF report from NDJSON."""
    rpt = reporter.generate_pdf(ndjson, output)
    if open_: import subprocess; subprocess.run(["open", rpt])

@report_app.command("last")
def report_last(fmt: str = typer.Option("html","--format","-f"),
                open_: bool = typer.Option(True,"--open")):
    """📄 Generate report from the most recent scan."""
    last = history.get_last_scan()
    if not last: console.print("[danger]No scan history.[/danger]"); raise typer.Exit(1)
    rpt = reporter.generate_pdf(last["output_file"]) if fmt=="pdf" else reporter.generate_html(last["output_file"])
    if open_: import subprocess; subprocess.run(["open", rpt])

# ── history ───────────────────────────────────────────────────────────────────
@history_app.callback(invoke_without_command=True)
def history_default(ctx: typer.Context,
                    limit: int = typer.Option(20, "--limit", "-n")):
    """Show recent scan history (default when called with no subcommand)."""
    if ctx.invoked_subcommand is None:
        history.show_history(limit)
@history_app.command("show")
def history_show(limit: int = typer.Option(20,"--limit","-n")):
    """📜 Show recent scan history."""
    history.show_history(limit)

@history_app.command("clear")
def history_clear(yes: bool = typer.Option(False,"--yes","-y")):
    """🗑  Clear all scan history."""
    if not yes: typer.confirm("Clear all history?", abort=True)
    history.clear_history()

@history_app.command("last")
def history_last():
    """🔍 Show details of the most recent scan."""
    last = history.get_last_scan()
    if not last: console.print("[muted]No history.[/muted]"); return
    console.print(Panel("\n".join(f"[muted]{k}:[/muted] [accent]{v}[/accent]"
                                  for k,v in last.items()),
                        title="[primary]🕐 Last Scan[/primary]", box=box.ROUNDED))

# ── catalog ───────────────────────────────────────────────────────────────────

@catalog_app.command("list")
def catalog_list():
    """📚 List local exposure catalogs."""
    catalog.list_catalogs()

@catalog_app.command("show")
def catalog_show(name: str = typer.Argument(...)):
    """🔍 Show catalog contents."""
    catalog.show_catalog(name)

@catalog_app.command("create")
def catalog_create(name: str = typer.Argument(...)):
    """✏️  Interactively build a new catalog."""
    entries = []
    while True:
        e = catalog.add_entry_interactive()
        if e: entries.append(e)
        if not typer.confirm("Add another entry?", default=False): break
    catalog.create_catalog(name, entries)

@catalog_app.command("validate")
def catalog_validate(path: str = typer.Argument(...)):
    """✅ Validate a catalog JSON file."""
    catalog.validate_catalog(path)

@catalog_app.command("fetch-intel")
def catalog_fetch_intel():
    """Fetch all available threat intel catalogs."""
    for name in catalog.KNOWN_THREAT_INTEL:
        catalog.fetch_threat_intel(name)

@catalog_app.command("list-intel")
def catalog_list_intel():
    """List all known threat intel sources."""
    catalog.list_known_threat_intel()

if __name__ == "__main__":
    app()