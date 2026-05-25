"""Track scan run metadata in ~/.bumblebee-cli/history.json"""
import json
from pathlib import Path
from datetime import datetime, timezone
from rich.table import Table
from rich import box
from bbcli.theme import console

HISTORY_FILE = Path.home() / ".bumblebee-cli" / "history.json"

def _load():
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text())
    except Exception:
        return []

def _save(records):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(records, indent=2))

def add_entry(profile, output_file, summary, findings_count):
    records = _load()
    records.append({
        "id":               len(records) + 1,
        "timestamp":        datetime.now(timezone.utc).isoformat() + "Z",
        "profile":          profile,
        "output_file":      output_file,
        "files_considered": summary.get("files_considered", 0),
        "records":          summary.get("records", 0),
        "findings":         findings_count,
        "status":           "clean" if findings_count == 0 else "findings",
    })
    _save(records)

def show_history(limit=20):
    records = _load()
    if not records:
        console.print("[muted]No scan history yet. Run:[/muted] [accent]bbcli scan[/accent]")
        return
    t = Table(title="📜 Scan History", box=box.DOUBLE_EDGE,
              title_style="primary", header_style="accent")
    t.add_column("#",        width=4, justify="right")
    t.add_column("Date/Time", style="muted")
    t.add_column("Profile",   style="accent")
    t.add_column("Files",     justify="right")
    t.add_column("Packages",  justify="right")
    t.add_column("Status")
    t.add_column("Output",    style="muted")
    for r in reversed(records[-limit:]):
        status = ("[success]✅ Clean[/success]" if r["findings"] == 0
                  else f"[danger]⚠️  {r['findings']} findings[/danger]")
        ts = r["timestamp"][:19].replace("T"," ")
        t.add_row(str(r["id"]), ts, r["profile"],
                  f"{r.get('files_considered',0):,}",
                  f"{r.get('records',0):,}",
                  status, Path(r.get("output_file","")).name)
    console.print(t)

def clear_history():
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
    console.print("[success]✅ History cleared.[/success]")

def get_last_scan():
    records = _load()
    return records[-1] if records else None