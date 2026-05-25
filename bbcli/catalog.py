"""Manage exposure catalogs — create, validate, list, and fetch threat intel."""
import json
import requests
from pathlib import Path
from datetime import datetime, timezone
from rich.table import Table
from rich.panel import Panel
from rich import box
from bbcli.theme import console, SEVERITY_STYLES

CATALOG_DIR = Path.home() / ".bumblebee-cli" / "catalogs"

KNOWN_THREAT_INTEL = {
    "trapdoor-crypto-stealer": {
        "url": "https://raw.githubusercontent.com/perplexityai/bumblebee/main/threat_intel/trapdoor-crypto-stealer.json",
        "description": "TrapDoor Crypto Stealer — malicious npm packages (2026)",
    },
}

def _ensure_dir():
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)

def create_catalog(name, entries):
    _ensure_dir()
    catalog = {
        "schema_version": "0.1.0",
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
        "name": name,
        "entries": entries,
    }
    out = CATALOG_DIR / f"{name}.json"
    out.write_text(json.dumps(catalog, indent=2))
    console.print(f"[success]✅ Catalog created:[/success] [accent]{out}[/accent] — [muted]{len(entries)} entries[/muted]")
    return str(out)

def add_entry_interactive():
    try:
        import questionary
        eco     = questionary.select("Ecosystem:", choices=["npm","pypi","go","rubygems","packagist","mcp","editor-extension","browser-extension"]).ask()
        pkg     = questionary.text("Package name:").ask()
        ver     = questionary.text("Version(s) — comma-separated:").ask()
        sev     = questionary.select("Severity:", choices=["critical","high","medium","low","info"]).ask()
        adv_id  = questionary.text("Advisory ID (e.g. CVE-2026-xxxx):").ask()
        adv_name= questionary.text("Advisory description:").ask()
    except ImportError:
        eco      = input("Ecosystem: ").strip()
        pkg      = input("Package name: ").strip()
        ver      = input("Versions (comma-sep): ").strip()
        sev      = input("Severity: ").strip()
        adv_id   = input("Advisory ID: ").strip()
        adv_name = input("Advisory description: ").strip()
    return {
        "id":        adv_id or f"custom-{pkg}-{ver}",
        "name":      adv_name or f"{pkg} {ver} (compromised)",
        "ecosystem": eco,
        "package":   pkg,
        "versions":  [v.strip() for v in ver.split(",") if v.strip()],
        "severity":  sev,
    }

def list_catalogs():
    _ensure_dir()
    files = list(CATALOG_DIR.glob("*.json"))
    if not files:
        console.print("[muted]No catalogs yet. Use:[/muted] [accent]bbcli catalog create[/accent]")
        return
    t = Table(title="📚 Exposure Catalogs", box=box.DOUBLE_EDGE,
              title_style="primary", header_style="accent")
    t.add_column("Name",    style="bold white")
    t.add_column("Entries", justify="right")
    t.add_column("Created", style="muted")
    t.add_column("Path",    style="muted")
    for f in files:
        try:
            data    = json.loads(f.read_text())
            entries = len(data.get("entries", []))
            created = data.get("created_at", "—")[:10]
        except Exception:
            entries, created = "?", "?"
        t.add_row(f.stem, str(entries), created, str(f))
    console.print(t)

def show_catalog(name_or_path):
    p = Path(name_or_path)
    if not p.exists():
        p = CATALOG_DIR / f"{name_or_path}.json"
    if not p.exists():
        console.print(f"[danger]Catalog not found:[/danger] {name_or_path}")
        return
    data = json.loads(p.read_text())
    t = Table(title=f"📚 {p.stem}", box=box.SIMPLE_HEAVY,
              title_style="primary", header_style="accent", show_lines=True)
    t.add_column("ID",        style="muted")
    t.add_column("Package",   style="bold white")
    t.add_column("Versions",  style="accent")
    t.add_column("Ecosystem", width=16)
    t.add_column("Severity")
    t.add_column("Description", style="muted")
    for e in data.get("entries", []):
        sev = e.get("severity", "info")
        sty = SEVERITY_STYLES.get(sev, "white")
        t.add_row(e.get("id",""), e.get("package",""),
                  ", ".join(e.get("versions",[])), e.get("ecosystem",""),
                  f"[{sty}]{sev.upper()}[/{sty}]", e.get("name",""))
    console.print(t)

def validate_catalog(path):
    try:
        data = json.loads(Path(path).read_text())
        assert "schema_version" in data, "missing schema_version"
        assert isinstance(data.get("entries"), list), "missing entries list"
        for e in data["entries"]:
            for k in ("id","name","ecosystem","package","versions","severity"):
                assert k in e, f"entry missing field: {k}"
        console.print(f"[success]✅ Valid:[/success] [accent]{path}[/accent] — [muted]{len(data['entries'])} entries[/muted]")
        return True
    except Exception as ex:
        console.print(f"[danger]❌ Invalid:[/danger] {ex}")
        return False

def fetch_threat_intel(name):
    entry = KNOWN_THREAT_INTEL.get(name)
    if not entry:
        console.print(f"[danger]Unknown:[/danger] {name}")
        console.print(f"[muted]Available:[/muted] {', '.join(KNOWN_THREAT_INTEL)}")
        return None
    _ensure_dir()
    out = CATALOG_DIR / f"{name}.json"
    console.print(f"[info]Fetching:[/info] [accent]{entry['description']}[/accent]")
    try:
        resp = requests.get(entry["url"], timeout=30)
        resp.raise_for_status()
        out.write_bytes(resp.content)
        console.print(f"[success]✅ Saved:[/success] [accent]{out}[/accent]")
        return str(out)
    except Exception as ex:
        console.print(f"[danger]❌ Fetch failed:[/danger] {ex}")
        return None

def list_known_threat_intel():
    t = Table(title="🛡  Known Threat Intel", box=box.ROUNDED,
              title_style="primary", header_style="accent")
    t.add_column("Name", style="bold white")
    t.add_column("Description", style="muted")
    for name, meta in KNOWN_THREAT_INTEL.items():
        t.add_row(name, meta["description"])
    console.print(t)