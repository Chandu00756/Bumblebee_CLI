"""Install, update, and verify Bumblebee binary."""
import subprocess, shutil, os
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from rich import box
from bbcli.theme import console

GO_PKG = "github.com/perplexityai/bumblebee/cmd/bumblebee@latest"

def _go_available() -> bool:
    return shutil.which("go") is not None

def _bumblebee_path() -> str | None:
    p = shutil.which("bumblebee")
    if p:
        return p
    gobin = os.environ.get("GOBIN") or os.path.join(os.path.expanduser("~"), "go", "bin")
    candidate = os.path.join(gobin, "bumblebee")
    return candidate if os.path.isfile(candidate) else None

def get_version() -> str:
    bb = _bumblebee_path()
    if not bb:
        return "not installed"
    try:
        r = subprocess.run([bb, "version"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip().splitlines()[0] if r.stdout.strip() else "unknown"
    except Exception:
        return "unknown"

def install(update: bool = False) -> bool:
    bb = _bumblebee_path()
    if bb and not update:
        console.print(f"[success]✅ Already installed:[/success] [muted]{bb}[/muted]")
        console.print(f"[muted]Version: {get_version()}[/muted]")
        console.print("[info]Tip:[/info] [muted]Run [accent]bee update[/accent] to upgrade.[/muted]")
        return True
    if not _go_available():
        console.print(Panel(
            "[danger]Go is not installed![/danger]\n\n"
            "Bumblebee requires Go 1.25+. Install from:\n"
            "[info]https://go.dev/dl/[/info]\n\n"
            "Then re-run: [accent]bbcli install[/accent]",
            title="[danger]❌ Missing Dependency[/danger]",
            style="danger", box=box.HEAVY
        ))
        return False
    verb = "Updating" if update else "Installing"
    console.print(f"\n[primary]{verb} Bumblebee (latest)…[/primary]")
    with Progress(
        SpinnerColumn(spinner_name="dots", style="primary"),
        TextColumn("[accent]{task.description}[/accent]"),
        BarColumn(bar_width=40, style="primary", complete_style="success"),
        TimeElapsedColumn(),
        console=console,
    ) as prog:
        task = prog.add_task(f"{verb} via go install…", total=None)
        result = subprocess.run(
            [shutil.which("go"), "install", GO_PKG],
            capture_output=True, text=True
        )
        prog.update(task, completed=100, total=100)
    if result.returncode != 0:
        console.print(f"[danger]❌ Failed:[/danger]\n{result.stderr}")
        return False
    console.print(f"[success]✅ Installed![/success] Version: {get_version()}")
    # Auto selftest
    bb = _bumblebee_path()
    if bb:
        r = subprocess.run([bb, "selftest"], capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            console.print(f"[success]✅ Selftest:[/success] [muted]{r.stdout.strip()}[/muted]")
    return True

def uninstall() -> bool:
    bb = _bumblebee_path()
    if not bb:
        console.print("[warning]⚠️  Not installed.[/warning]")
        return False
    os.remove(bb)
    console.print(f"[success]✅ Removed:[/success] [muted]{bb}[/muted]")
    return True

def status() -> dict:
    bb = _bumblebee_path()
    return {
        "installed":    bb is not None,
        "path":         bb or "—",
        "version":      get_version() if bb else "—",
        "go_available": _go_available(),
    }