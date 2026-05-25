"""Interactive guided menu — for beginners who prefer a UI over flags."""
import os
from pathlib import Path
from datetime import datetime
from bbcli.theme import console, BANNER
from bbcli import scanner, installer, scheduler, reporter, history, catalog

def _q(prompt, choices):
    try:
        import questionary
        return questionary.select(prompt, choices=choices).ask() or choices[0]
    except ImportError:
        for i,c in enumerate(choices,1): console.print(f"  [accent]{i})[/accent] {c}")
        val = input("Choice: ").strip()
        try: return choices[int(val)-1]
        except: return choices[0]

def _t(prompt, default=""):
    try:
        import questionary
        return questionary.text(prompt, default=default).ask() or default
    except ImportError:
        val = input(f"{prompt} [{default}]: ").strip()
        return val or default

def _c(prompt, default=True):
    try:
        import questionary
        r = questionary.confirm(prompt, default=default).ask()
        return r if r is not None else default
    except ImportError:
        val = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
        return val.startswith("y") if val else default

def _out(profile):
    d = Path.home() / ".bumblebee-cli" / "scans"
    d.mkdir(parents=True, exist_ok=True)
    return str(d / f"scan_{profile}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ndjson")

def run_interactive():
    console.print(BANNER)
    while True:
        action = _q("🐝 What would you like to do?", [
            "🔍  Run a scan",
            "⚡  Quick baseline scan",
            "🚨  Threat intelligence scan",
            "📅  Schedule a scan",
            "📊  View scan history",
            "📄  Generate a report",
            "🛡   Manage catalogs",
            "📋  Preview scan roots",
            "⚙️   Check Bumblebee status",
            "🔧  Install / Update Bumblebee",
            "✅  Run selftest",
            "❌  Exit",
        ])
        if not action or action.startswith("❌"):
            console.print("[primary]👋 Stay secure. 🐝[/primary]")
            break
        elif action.startswith("🔍"):  _do_scan()
        elif action.startswith("⚡"):  _do_quick()
        elif action.startswith("🚨"):  _do_threat()
        elif action.startswith("📅"):  _do_schedule()
        elif action.startswith("📊"):  history.show_history()
        elif action.startswith("📄"):  _do_report()
        elif action.startswith("🛡"):  _do_catalogs()
        elif action.startswith("📋"):  _do_roots()
        elif action.startswith("⚙️"):  _do_status()
        elif action.startswith("🔧"):  installer.install(update=_c("Force update?", False))
        elif action.startswith("✅"):  scanner.run_selftest()

def _do_scan():
    profile = _q("Profile:", ["baseline","project","deep"])
    roots   = [x.strip() for x in _t("Root dirs (blank=auto):", "").split(",") if x.strip()]
    ecosystems = [e.strip() for e in _t("Ecosystems (blank=all):","").split(",") if e.strip()]
    cat_path = None
    if _c("Use an exposure catalog?", False):
        catalog.list_catalogs()
        name = _t("Catalog name or path:")
        if name:
            p = Path(name)
            cat_path = str(p) if p.exists() else str(catalog.CATALOG_DIR / f"{name}.json")
    out = _out(profile)
    result = scanner.run_scan(profile, roots, ecosystems, cat_path, False, None, out)
    if result:
        scanner.show_scan_results(result)
        history.add_entry(profile, out, result.get("summary",{}), len(result.get("findings",[])))
        _offer_report(out)

def _do_quick():
    out = _out("baseline")
    result = scanner.run_scan("baseline",[],[],None,False,None,out)
    if result:
        scanner.show_scan_results(result)
        history.add_entry("baseline", out, result.get("summary",{}), len(result.get("findings",[])))
        _offer_report(out)

def _do_threat():
    catalog.list_known_threat_intel()
    name = _t("Catalog name:", "trapdoor-crypto-stealer")
    cat_path = catalog.CATALOG_DIR / f"{name}.json"
    if not cat_path.exists():
        res = catalog.fetch_threat_intel(name)
        if not res: return
    roots = [x.strip() for x in _t("Root dirs (blank=home):","").split(",") if x.strip()] or [str(Path.home())]
    out = _out("deep")
    result = scanner.run_scan("deep", roots, [], str(cat_path), True, "10m", out)
    if result:
        scanner.show_scan_results(result)
        history.add_entry("deep", out, result.get("summary",{}), len(result.get("findings",[])))
        _offer_report(out)

def _do_schedule():
    action = _q("Schedule action:", ["Add new","List all","Remove","Trigger now"])
    if action.startswith("Add"):
        name    = _t("Schedule name:", "daily-scan")
        profile = _q("Profile:", ["baseline","project","deep"])
        roots   = [x.strip() for x in _t("Root dirs:","").split(",") if x.strip()]
        when    = _q("When?", ["daily","morning","evening","hourly","weekly","monthly"])
        out_dir = _t("Output dir:", str(Path.home()/".bumblebee-cli"/"scans"))
        scheduler.add_schedule(name, profile, roots, [], None, False, when, out_dir)
    elif action.startswith("List"):
        scheduler.show_schedules()
    elif action.startswith("Remove"):
        scheduler.show_schedules()
        name = _t("Name to remove:")
        if name: scheduler.remove_schedule(name)
    elif action.startswith("Trigger"):
        scheduler.show_schedules()
        name = _t("Name to trigger:")
        if name: scheduler.run_now(name)

def _do_report():
    last = history.get_last_scan()
    path = _t("NDJSON path:", last["output_file"] if last else "")
    if not path or not os.path.exists(path):
        console.print("[danger]File not found.[/danger]"); return
    fmt = _q("Format:", ["HTML","PDF"])
    rpt = reporter.generate_pdf(path) if fmt=="PDF" else reporter.generate_html(path)
    if _c("Open it?", True):
        import subprocess; subprocess.run(["open", rpt])

def _do_catalogs():
    action = _q("Catalog action:", [
        "List my catalogs","Show contents","Create new",
        "Fetch threat intel","Validate","List known threat intel"
    ])
    if action.startswith("List my"):      catalog.list_catalogs()
    elif action.startswith("Show"):
        catalog.show_catalog(_t("Name or path:"))
    elif action.startswith("Create"):
        name = _t("Catalog name:")
        entries = []
        while True:
            e = catalog.add_entry_interactive()
            if e: entries.append(e)
            if not _c("Add another?", False): break
        catalog.create_catalog(name, entries)
    elif action.startswith("Fetch"):
        catalog.list_known_threat_intel()
        catalog.fetch_threat_intel(_t("Name:"))
    elif action.startswith("Validate"):
        catalog.validate_catalog(_t("Path:"))
    elif action.startswith("List known"):
        catalog.list_known_threat_intel()

def _do_roots():
    profile = _q("Profile:", ["baseline","project","deep"])
    roots   = [x.strip() for x in _t("Root dirs:","").split(",") if x.strip()]
    scanner.run_roots(profile, roots)

def _do_status():
    from rich.table import Table
    from rich import box as rbox
    s = installer.status()
    t = Table(title="⚙️  Bumblebee Status", box=rbox.DOUBLE_EDGE,
              title_style="primary", header_style="accent")
    t.add_column("Property", style="muted")
    t.add_column("Value",    style="bold white")
    t.add_row("Installed",    "[success]✅ Yes[/success]" if s["installed"] else "[danger]❌ No[/danger]")
    t.add_row("Version",      s["version"])
    t.add_row("Binary Path",  s["path"])
    t.add_row("Go Available", "[success]✅ Yes[/success]" if s["go_available"] else "[danger]❌ No[/danger]")
    console.print(t)

def _offer_report(out):
    if _c("Generate a report?", True):
        fmt = _q("Format:", ["HTML","PDF"])
        rpt = reporter.generate_pdf(out) if fmt=="PDF" else reporter.generate_html(out)
        if _c("Open it?", True):
            import subprocess; subprocess.run(["open", rpt])