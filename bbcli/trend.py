"""Historical trend analysis — findings over time from scan history."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from rich.table import Table
from rich.panel import Panel
from rich import box
from bbcli.theme import console
from bbcli.history import _load as load_history

_SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]

_SPARK_CHARS = " ▁▂▃▄▅▆▇█"


def _sparkline(values: list[int]) -> str:
    if not values:
        return ""
    max_v = max(values) or 1
    return "".join(_SPARK_CHARS[int(v / max_v * (len(_SPARK_CHARS) - 1))] for v in values)


def _count_from_ndjson(path: str) -> dict[str, int]:
    counts: dict[str, int] = {s: 0 for s in _SEVERITY_ORDER}
    try:
        for line in Path(path).read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("record_type") == "finding":
                sev = (rec.get("severity") or "info").lower()
                if sev in counts:
                    counts[sev] += 1
                else:
                    counts["info"] += 1
    except (FileNotFoundError, PermissionError):
        pass
    return counts


def show_trend(limit: int = 10) -> None:
    """Print a trend table + sparkline chart from scan history."""
    from bbcli import __version__
    console.print(f"[primary]🐝 Bumblebee CLI[/primary] [muted]v{__version__} — Dependency security scanner for macOS[/muted]")

    records = load_history()
    if not records:
        console.print("[muted]No scan history yet. Run [accent]bee scan[/accent] first.[/muted]")
        return

    recent = records[-limit:]

    # Build trend table
    t = Table(
        title=f"📈 Findings Trend  (last {len(recent)} scans)",
        box=box.DOUBLE_EDGE, title_style="primary", header_style="accent",
    )
    t.add_column("#",        width=4,  justify="right")
    t.add_column("Date",     style="muted")
    t.add_column("Profile",  style="accent")
    t.add_column("Critical", justify="right", style="critical")
    t.add_column("High",     justify="right", style="high")
    t.add_column("Medium",   justify="right", style="medium")
    t.add_column("Low",      justify="right", style="low")
    t.add_column("Total",    justify="right", style="bold")
    t.add_column("Δ",        justify="right")

    prev_total = None
    all_totals = []

    rows_data = []
    for r in recent:
        ndjson = r.get("output_file", "")
        counts = _count_from_ndjson(ndjson) if ndjson and Path(ndjson).exists() else {
            s: 0 for s in _SEVERITY_ORDER
        }
        # Fall back to history total if file is gone
        total = sum(counts.values()) or r.get("findings", 0)
        counts["_total"] = total
        rows_data.append((r, counts))
        all_totals.append(total)

    for i, (r, counts) in enumerate(rows_data):
        total = counts["_total"]
        ts    = r.get("timestamp", "")[:19].replace("T", " ")

        if prev_total is None:
            delta_str = "[muted]—[/muted]"
        elif total > prev_total:
            delta_str = f"[danger]+{total - prev_total}[/danger]"
        elif total < prev_total:
            delta_str = f"[success]-{prev_total - total}[/success]"
        else:
            delta_str = "[muted]0[/muted]"

        t.add_row(
            str(r.get("id", i + 1)),
            ts,
            r.get("profile", ""),
            str(counts.get("critical", 0)) if counts.get("critical") else "[muted]0[/muted]",
            str(counts.get("high", 0))     if counts.get("high")     else "[muted]0[/muted]",
            str(counts.get("medium", 0))   if counts.get("medium")   else "[muted]0[/muted]",
            str(counts.get("low", 0))      if counts.get("low")      else "[muted]0[/muted]",
            str(total),
            delta_str,
        )
        prev_total = total

    console.print(t)

    # Sparkline
    spark = _sparkline(all_totals)
    direction = ""
    if len(all_totals) >= 2:
        if all_totals[-1] < all_totals[0]:
            direction = "  [success]↘ Improving[/success]"
        elif all_totals[-1] > all_totals[0]:
            direction = "  [danger]↗ Worsening[/danger]"
        else:
            direction = "  [muted]→ Stable[/muted]"

    console.print(Panel(
        f"  [accent]{spark}[/accent]{direction}\n"
        f"  [muted]min:[/muted] {min(all_totals)}  "
        f"[muted]max:[/muted] {max(all_totals)}  "
        f"[muted]latest:[/muted] {all_totals[-1]}",
        title="Findings Sparkline",
        border_style="accent",
        expand=False,
    ))
