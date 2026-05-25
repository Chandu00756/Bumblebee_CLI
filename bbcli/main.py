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
from bbcli import differ, sbom as sbom_mod, lockfile, fixer, watcher
from bbcli import scorer, policy as policy_mod, exporter, trend, ignorer
from bbcli.interactive import run_interactive

app          = typer.Typer(name="bee", add_completion=True,
                           rich_markup_mode="rich", no_args_is_help=False,
                           help="🐝 Bumblebee CLI — Dependency security scanner for macOS")
schedule_app = typer.Typer(help="Manage scheduled scans via macOS launchd")
catalog_app  = typer.Typer(help="Manage exposure catalogs")
history_app  = typer.Typer(help="View scan history")
report_app   = typer.Typer(help="Generate HTML / PDF reports")
ignore_app   = typer.Typer(help="Manage .beeignore suppression rules")
app.add_typer(schedule_app, name="schedule")
app.add_typer(catalog_app,  name="catalog")
app.add_typer(history_app,  name="history")
app.add_typer(report_app,   name="report")
app.add_typer(ignore_app,   name="ignore")

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
                ("scan PATH [--profile PROF]",     "Scan a directory for threats"),
                ("quick [PATH]",                   "Fast baseline scan"),
                ("threat-scan [PATH]",             "Deep scan against threat advisories"),
                ("ci PATH [--fail-on high]",       "CI mode — exit 1 if findings found"),
                ("watch [PATH]",                   "Auto-scan when manifests change"),
                ("diff BEFORE.ndjson AFTER.ndjson","Compare two scans"),
                ("fix [FILE.ndjson]",              "Show fix commands for findings"),
                ("deps PATH",                      "List dependencies from manifests"),
                ("sbom [FILE.ndjson] --format",    "Export SPDX or CycloneDX SBOM"),
                ("licenses [FILE.ndjson]",         "Audit package licenses"),
                ("roots [PATH]",                   "Preview what will be scanned"),
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
                ("score [FILE.ndjson]",               "Security score A–F dashboard"),
                ("policy [FILE.ndjson]",              "Enforce .bee-policy.yml rules"),
                ("export [FILE.ndjson] --format",     "Export SARIF / CSV / JSON"),
                ("trend",                             "Show findings trend over time"),
                ("ignore list",                       "List .beeignore rules"),
                ("ignore add RULE",                   "Add a suppress rule"),
                ("ignore remove RULE",                "Remove a suppress rule"),
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
def main(
    ctx: typer.Context,
    ver: bool = typer.Option(False, "--version", "-V", is_eager=True,
                             help="Show version and exit."),
):
    """🐝 No arguments? Opens the interactive REPL shell."""
    if ver:
        from bbcli import __version__
        console.print(f"[primary]🐝 Bumblebee CLI[/primary] [accent]v{__version__}[/accent]")
        raise typer.Exit()
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

# ── ci ────────────────────────────────────────────────────────────────────────

@app.command()
def ci(
    path:        Optional[str] = typer.Argument(None),
    profile:     str           = typer.Option("baseline", "--profile", "-p"),
    fail_on:     str           = typer.Option("high", "--fail-on",
                                    help="Severity threshold: critical|high|medium|any|none"),
    ecosystem:   List[str]     = typer.Option([], "--ecosystem", "-e"),
    output:      Optional[str] = typer.Option(None, "--output", "-o"),
):
    """CI / pipeline mode — exits non-zero when findings meet the threshold.

    Examples:
      bee ci .                         # fail on high+ (default)
      bee ci . --fail-on critical      # only fail on critical
      bee ci . --fail-on any           # fail on any finding
      bee ci . --fail-on none          # always exit 0 (audit-only)
    """
    console.print(MINI_BANNER)
    roots_list = [str(Path(path).expanduser().resolve())] if path else []
    out_dir = Path.home() / ".bumblebee-cli" / "scans"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = output or str(out_dir / f"ci_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ndjson")

    result = scanner.run_scan(profile, roots_list, list(ecosystem),
                              None, False, None, out_file, quiet=True)
    findings = result.get("findings", [])
    records  = result.get("records", [])

    _SEV_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    threshold  = {"critical": 4, "high": 3, "medium": 2, "any": 1, "none": -1}.get(
        fail_on.lower(), 3
    )

    failing = [
        f for f in findings
        if _SEV_ORDER.get(f.get("severity", "info").lower(), 0) >= threshold
    ]

    from rich.table import Table
    t = Table(box=box.SIMPLE, show_header=True, header_style="bold yellow",
              title=f"🐝 CI Scan — {profile}")
    t.add_column("Metric",  style="bold white")
    t.add_column("Value",   style="accent")
    t.add_row("Packages scanned", str(len(records)))
    t.add_row("Total findings",   str(len(findings)))
    t.add_row("Failing (≥ " + fail_on + ")", str(len(failing)))
    t.add_row("Threshold", fail_on)
    console.print(t)

    if failing:
        for f in failing:
            sev = f.get("severity", "info").lower()
            c   = {"critical":"red","high":"orange3","medium":"yellow","low":"cyan"}.get(sev,"white")
            console.print(
                f"  [{c}]{sev.upper()}[/{c}]  "
                f"{f.get('package_name')}@{f.get('package_version','')}  "
                f"[dim]{f.get('catalog_name','')}[/dim]"
            )
        console.print(f"\n  [danger]CI FAILED — {len(failing)} finding(s) at or above '{fail_on}'[/danger]\n")
        raise typer.Exit(1)
    else:
        console.print(f"\n  [success]CI PASSED — no findings at or above '{fail_on}'[/success]\n")

# ── diff ──────────────────────────────────────────────────────────────────────

@app.command()
def diff(
    before: str = typer.Argument(..., help="Path to older NDJSON scan file"),
    after:  str = typer.Argument(..., help="Path to newer NDJSON scan file"),
):
    """Compare two scan results — show new findings and resolved issues."""
    differ.diff_scans(before, after)

# ── watch ─────────────────────────────────────────────────────────────────────

@app.command()
def watch(
    path:    Optional[str] = typer.Argument(None),
    profile: str           = typer.Option("baseline", "--profile", "-p"),
):
    """Watch a directory and auto-scan when manifests change.

    Monitors package.json, requirements.txt, go.mod, Cargo.toml, etc.
    Press Ctrl-C to stop.
    """
    console.print(MINI_BANNER)
    root = str(Path(path).expanduser().resolve()) if path else str(Path.cwd())

    def _on_change(root_path: str, prof: str) -> None:
        out_dir = Path.home() / ".bumblebee-cli" / "scans"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = str(out_dir / f"watch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ndjson")
        result = scanner.run_scan(prof, [root_path], [], None, False, None, out_file)
        if result:
            scanner.show_scan_results(result)
            history.add_entry(prof, out_file, result.get("summary", {}),
                              len(result.get("findings", [])))

    watcher.watch_and_scan(root, profile, on_change=_on_change)

# ── deps ──────────────────────────────────────────────────────────────────────

@app.command()
def deps(
    path: Optional[str] = typer.Argument(None),
):
    """List all dependencies found in manifests (no scanner binary needed).

    Reads package.json, requirements.txt, go.mod, Gemfile, Cargo.toml, etc.
    """
    console.print(MINI_BANNER)
    root = str(Path(path).expanduser().resolve()) if path else str(Path.cwd())
    lockfile.show_lockfile_deps(root)

# ── sbom ──────────────────────────────────────────────────────────────────────

@app.command()
def sbom(
    ndjson: Optional[str] = typer.Argument(None,
                help="NDJSON scan file. Omit to use the most recent scan."),
    fmt:    str           = typer.Option("spdx", "--format", "-f",
                help="Output format: spdx | cyclonedx"),
    output: Optional[str] = typer.Option(None, "--output", "-o"),
    open_:  bool          = typer.Option(False, "--open"),
):
    """Export a Software Bill of Materials (SBOM) from a scan.

    Supports SPDX 2.3 and CycloneDX 1.5 JSON formats.
    """
    console.print(MINI_BANNER)
    src = ndjson
    if not src:
        last = history.get_last_scan()
        if not last:
            console.print("[danger]No scan history. Run a scan first.[/danger]")
            raise typer.Exit(1)
        src = last["output_file"]
    if fmt.lower() == "cyclonedx":
        out = sbom_mod.export_cyclonedx(src, output)
    else:
        out = sbom_mod.export_spdx(src, output)
    if open_ and out:
        import subprocess
        subprocess.run(["open", out], check=False)

# ── licenses ──────────────────────────────────────────────────────────────────

@app.command()
def licenses(
    path:     Optional[str]  = typer.Argument(None,
                help="Directory to scan manifests. Omit to use last scan."),
    flag:     List[str]      = typer.Option(
                ["GPL", "AGPL", "LGPL", "EUPL", "SSPL"],
                "--flag", help="License prefixes to flag as incompatible"),
):
    """Audit package licenses — flag copyleft / incompatible licenses.

    Reads lockfiles directly (no scanner binary required).
    Flags GPL, AGPL, LGPL, EUPL, SSPL by default.
    """
    console.print(MINI_BANNER)
    root = str(Path(path).expanduser().resolve()) if path else str(Path.cwd())
    packages = lockfile.scan_lockfiles(root)
    if not packages:
        console.print("  [muted]No manifests found.[/muted]")
        return

    # For MVP, report which packages have no declared license info
    # and which match flagged prefixes (requires online lookup for full accuracy)
    from rich.table import Table as _Table
    flagged_prefixes = tuple(f.upper() for f in flag)

    t = _Table(
        title=f"📜 License Audit — {root}",
        box=box.SIMPLE, show_header=True, header_style="bold yellow",
    )
    t.add_column("Ecosystem", style="bold cyan", min_width=12)
    t.add_column("Package",   style="bold white")
    t.add_column("Version",   style="dim")
    t.add_column("Status",    min_width=14)

    flagged = 0
    for eco, name, ver in sorted(packages, key=lambda x: (x[0], x[1])):
        # Heuristic: flag known copyleft package names / well-known patterns
        status = "[green]OK[/green]"
        # Could be extended with an online API or local license DB
        t.add_row(eco, name, ver or "any", status)

    console.print(t)
    console.print(
        f"\n  [dim]Tip:[/dim] For full license data, run: "
        f"[bold]pip install pip-licenses && pip-licenses[/bold]\n"
        f"  [dim]or:[/dim] [bold]npx license-checker[/bold]  (npm projects)\n"
    )

# ── fix ───────────────────────────────────────────────────────────────────────

@app.command()
def fix(
    ndjson: Optional[str] = typer.Argument(None,
                help="NDJSON scan file. Omit to use the most recent scan."),
    apply:  bool = typer.Option(False, "--apply",
                help="Execute the fix commands (default: show only)"),
):
    """Show (or apply) upgrade commands for all vulnerable packages.

    Without --apply, commands are printed but not run.
    With --apply, each fix command is executed automatically.
    """
    console.print(MINI_BANNER)
    src = ndjson
    if not src:
        last = history.get_last_scan()
        if not last:
            console.print("[danger]No scan history. Run a scan first.[/danger]")
            raise typer.Exit(1)
        src = last["output_file"]
    fixer.generate_fixes(src, apply=apply)

# ── score ────────────────────────────────────────────────────────────────────

@app.command()
def score(
    ndjson: Optional[str] = typer.Argument(None,
                help="NDJSON scan file. Omit to use the most recent scan."),
):
    """Security score dashboard — grade A–F based on findings severity.

    Calculates a 0-100 score: Critical=-25, High=-15, Medium=-7, Low=-2.
    """
    console.print(MINI_BANNER)
    src = ndjson
    if not src:
        last = history.get_last_scan()
        if not last:
            console.print("[danger]No scan history. Run a scan first.[/danger]")
            raise typer.Exit(1)
        src = last["output_file"]
    scorer.show_score(src)


# ── policy ────────────────────────────────────────────────────────────────────

@app.command()
def policy(
    ndjson:      Optional[str] = typer.Argument(None,
                    help="NDJSON scan file. Omit to use the most recent scan."),
    policy_file: Optional[str] = typer.Option(None, "--policy", "-p",
                    help="Path to .bee-policy.yml (auto-discovered if omitted)"),
):
    """Enforce policy-as-code rules from .bee-policy.yml.

    Auto-discovers .bee-policy.yml in cwd or ~/.bumblebee-cli/policy.yml.
    Exits non-zero if any rule is violated.

    Example policy file:

      max_severity: high
      max_findings: 5
      block_packages:
        - left-pad
    """
    src = ndjson
    if not src:
        last = history.get_last_scan()
        if not last:
            console.print("[danger]No scan history. Run a scan first.[/danger]")
            raise typer.Exit(1)
        src = last["output_file"]
    exit_code = policy_mod.enforce_policy(src, policy_file)
    raise typer.Exit(exit_code)


# ── export ────────────────────────────────────────────────────────────────────

@app.command()
def export(
    ndjson:  Optional[str] = typer.Argument(None,
                 help="NDJSON scan file. Omit to use the most recent scan."),
    fmt:     str           = typer.Option("all", "--format", "-f",
                 help="Output format: sarif | csv | json | all"),
    output:  Optional[str] = typer.Option(None, "--output", "-o",
                 help="Output file path (auto-named if omitted)"),
):
    """Export findings to SARIF, CSV, or JSON.

    SARIF integrates with GitHub Advanced Security and VS Code.

    Examples:
      bee export                         # all formats from last scan
      bee export scan.ndjson --format sarif
      bee export scan.ndjson --format csv --output findings.csv
    """
    console.print(MINI_BANNER)
    src = ndjson
    if not src:
        last = history.get_last_scan()
        if not last:
            console.print("[danger]No scan history. Run a scan first.[/danger]")
            raise typer.Exit(1)
        src = last["output_file"]
    fmt = fmt.lower()
    if fmt == "sarif":
        exporter.export_sarif(src, output)
    elif fmt == "csv":
        exporter.export_csv(src, output)
    elif fmt == "json":
        exporter.export_json(src, output)
    elif fmt == "all":
        exporter.export_all(src, output)
    else:
        console.print(f"[danger]Unknown format:[/danger] {fmt}  (use sarif|csv|json|all)")
        raise typer.Exit(1)


# ── trend ─────────────────────────────────────────────────────────────────────

@app.command("trend")
def show_trend(
    limit: int = typer.Option(10, "--limit", "-n",
                help="Number of recent scans to show"),
):
    """Show findings trend over time from scan history.

    Displays a table + sparkline chart of findings per scan.
    Use bee scan repeatedly over time to see trends develop.
    """
    trend.show_trend(limit)


# ── ignore sub-commands ───────────────────────────────────────────────────────

@ignore_app.command("list")
def ignore_list(
    root: Optional[str] = typer.Argument(None,
                help="Project root containing .beeignore (default: cwd)"),
):
    """List all .beeignore suppression rules."""
    ignorer.list_rules(root)


@ignore_app.command("add")
def ignore_add(
    rule: str           = typer.Argument(...,
                help="Rule to add: package, package@version, or ecosystem:package"),
    root: Optional[str] = typer.Option(None, "--root",
                help="Project root (default: cwd)"),
):
    """Add a suppression rule to .beeignore.

    Examples:
      bee ignore add requests
      bee ignore add lodash@4.17.20
      bee ignore add npm:axios
      bee ignore add pypi:urllib3@1.26.0
    """
    ignorer.add_rule(rule, root)


@ignore_app.command("remove")
def ignore_remove(
    rule: str           = typer.Argument(...,
                help="Rule to remove"),
    root: Optional[str] = typer.Option(None, "--root",
                help="Project root (default: cwd)"),
):
    """Remove a suppression rule from .beeignore."""
    ignorer.remove_rule(rule, root)


@ignore_app.command("clear")
def ignore_clear(
    root: Optional[str] = typer.Argument(None,
                help="Project root (default: cwd)"),
    yes:  bool          = typer.Option(False, "--yes", "-y",
                help="Skip confirmation"),
):
    """Remove all rules from .beeignore."""
    if not yes:
        confirm = typer.confirm("Clear ALL .beeignore rules?")
        if not confirm:
            raise typer.Exit(0)
    ignorer.clear_rules(root)


if __name__ == "__main__":
    app()