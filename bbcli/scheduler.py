"""
Scheduler module for Bumblebee CLI.

Creates and manages macOS launchd plist jobs for scheduled scans.
Supports add / remove / enable / disable / list / run-now / logs.
"""

from __future__ import annotations

import glob
import os
import platform
import plistlib
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich.panel import Panel
from rich.table import Table
from rich import box

from bbcli.theme import console

# ── constants ─────────────────────────────────────────────────────────────────
LABEL_PREFIX  = "com.bumblebee-cli"
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
LAUNCH_LOGS   = Path.home() / "Library" / "Logs"
IS_MACOS      = platform.system() == "Darwin"


# ── schedule presets ──────────────────────────────────────────────────────────
#   8 named presets; "hourly" maps to StartInterval instead of StartCalendarInterval
_PRESETS: dict[str, dict] = {
    "morning":  {"Hour": 8,  "Minute": 0},
    "noon":     {"Hour": 12, "Minute": 0},
    "daily":    {"Hour": 9,  "Minute": 0},
    "evening":  {"Hour": 18, "Minute": 0},
    "night":    {"Hour": 22, "Minute": 0},
    "weekly":   {"Hour": 9,  "Minute": 0, "Weekday": 1},
    "monthly":  {"Hour": 9,  "Minute": 0, "Day": 1},
    "hourly":   {},   # sentinel
}


def _interval_from_human(when: str) -> dict:
    """
    Translate a human-readable schedule string into a launchd trigger dict.

    Returns:
        {"start_interval": 3600}             for hourly
        {"start_calendar": {"Hour":H, ...}}  for everything else

    Accepted values:
        morning | noon | daily | evening | night | weekly | monthly | hourly | HH:MM
    """
    key = when.strip().lower()

    if key == "hourly":
        return {"start_interval": 3600}

    if key in _PRESETS:
        return {"start_calendar": dict(_PRESETS[key])}

    if ":" in key:
        try:
            h, m = key.split(":", 1)
            return {"start_calendar": {"Hour": int(h), "Minute": int(m)}}
        except (ValueError, TypeError):
            pass

    console.print(
        f"[warning]⚠ Unrecognised schedule '{when}', defaulting to daily 09:00[/warning]"
    )
    return {"start_calendar": {"Hour": 9, "Minute": 0}}


# ── internal helpers ──────────────────────────────────────────────────────────

def _bbcli_path() -> str:
    return shutil.which("bee") or shutil.which("bbcli") or sys.executable


def _plist_path(name: str) -> Path:
    return LAUNCH_AGENTS / f"{LABEL_PREFIX}.{name}.plist"


def _label(name: str) -> str:
    return f"{LABEL_PREFIX}.{name}"


def _log_paths(name: str) -> tuple[str, str]:
    lbl = _label(name)
    return (
        str(LAUNCH_LOGS / f"{lbl}.log"),
        str(LAUNCH_LOGS / f"{lbl}-error.log"),
    )


def _is_loaded(label: str) -> bool:
    if not IS_MACOS:
        return False
    res = subprocess.run(["launchctl", "list", label], capture_output=True, text=True)
    return res.returncode == 0


def _build_plist_dict(
    label: str,
    program_args: list[str],
    trigger: dict,
    log_out: str,
    log_err: str,
    working_dir: str,
) -> dict:
    gopath   = os.environ.get("GOPATH", str(Path.home() / "go"))
    go_bin   = str(Path(gopath) / "bin")
    cur_path = os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
    aug_path = f"{go_bin}:/usr/local/go/bin:{cur_path}"

    plist: dict = {
        "Label":            label,
        "ProgramArguments": program_args,
        "EnvironmentVariables": {
            "PATH":   aug_path,
            "GOPATH": gopath,
            "HOME":   str(Path.home()),
        },
        "StandardOutPath":   log_out,
        "StandardErrorPath": log_err,
        "WorkingDirectory":  working_dir,
        "RunAtLoad":         False,
    }

    if "start_interval" in trigger:
        plist["StartInterval"] = trigger["start_interval"]
    else:
        plist["StartCalendarInterval"] = trigger["start_calendar"]

    return plist


def _build_scan_args(
    name: str,
    profile: str,
    roots: List[str],
    ecosystems: List[str],
    exposure_catalog: Optional[str],
    findings_only: bool,
    output_dir: str,
) -> list[str]:
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = os.path.join(output_dir, f"sched_{name}_{ts}.ndjson")
    args     = [_bbcli_path(), "scan", "--profile", profile, "--output", out_file]
    for r in roots:
        args += ["--root", r]
    for e in ecosystems:
        args += ["--ecosystem", e]
    if exposure_catalog:
        args += ["--catalog", exposure_catalog]
    if findings_only and exposure_catalog:
        args.append("--findings-only")
    return args


# ── public API ────────────────────────────────────────────────────────────────

def add_schedule(
    name: str,
    profile: str,
    roots: List[str],
    ecosystems: List[str],
    exposure_catalog: Optional[str],
    findings_only: bool,
    when: str,
    output_dir: str,
) -> bool:
    """
    Register a new scheduled scan as a macOS launchd job.

    Writes ~/Library/LaunchAgents/com.bumblebee-cli.<name>.plist and runs
    `launchctl load -w` to register it immediately. Shows a Rich info panel
    confirming every detail on success.
    """
    plist = _plist_path(name)
    if plist.exists():
        console.print(f"[danger]❌ Schedule '{name}' already exists.[/danger]")
        return False

    lbl              = _label(name)
    trigger          = _interval_from_human(when)
    log_out, log_err = _log_paths(name)
    work_dir         = output_dir or str(Path.home() / ".bumblebee-cli" / "scans")

    Path(work_dir).mkdir(parents=True, exist_ok=True)
    LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
    LAUNCH_LOGS.mkdir(parents=True, exist_ok=True)

    args       = _build_scan_args(name, profile, roots, ecosystems,
                                   exposure_catalog, findings_only, work_dir)
    plist_dict = _build_plist_dict(lbl, args, trigger, log_out, log_err, work_dir)

    with open(plist, "wb") as fh:
        plistlib.dump(plist_dict, fh)

    loaded = False
    if IS_MACOS:
        res    = subprocess.run(
            ["launchctl", "load", "-w", str(plist)],
            capture_output=True, text=True,
        )
        loaded = res.returncode == 0
        if not loaded:
            console.print(f"[warning]⚠ launchctl load: {res.stderr.strip()}[/warning]")

    status_str = "[success]loaded ✓[/success]" if loaded else "[warning]saved (not loaded)[/warning]"
    info = "\n".join([
        f"  [dim]Name      :[/dim]  {name}",
        f"  [dim]Profile   :[/dim]  {profile}",
        f"  [dim]Schedule  :[/dim]  {when}",
        f"  [dim]Roots     :[/dim]  {', '.join(roots) or '(project root)'}",
        f"  [dim]Ecosystems:[/dim]  {', '.join(ecosystems) or '(all)'}",
        f"  [dim]Output    :[/dim]  {work_dir}",
        f"  [dim]Plist     :[/dim]  {plist}",
        f"  [dim]Logs      :[/dim]  {log_out}",
        f"  [dim]Status    :[/dim]  {status_str}",
    ])
    console.print(Panel(
        info,
        title="[primary]📅 Schedule Created[/primary]",
        border_style="primary",
        expand=False,
    ))
    return True


def list_schedules() -> list[dict]:
    """
    Scan ~/Library/LaunchAgents for com.bumblebee-cli.*.plist files.

    Reads each plist, checks whether it is currently loaded in launchd,
    and returns a list of descriptor dicts.
    """
    if not LAUNCH_AGENTS.exists():
        return []

    results: list[dict] = []
    pattern = str(LAUNCH_AGENTS / f"{LABEL_PREFIX}.*.plist")

    for plist_file in sorted(glob.glob(pattern)):
        path = Path(plist_file)
        name = path.stem.removeprefix(f"{LABEL_PREFIX}.")
        lbl  = _label(name)

        try:
            with open(path, "rb") as fh:
                data = plistlib.load(fh)
        except Exception:
            data = {}

        if "StartInterval" in data:
            when_str = f"every {data['StartInterval'] // 60} min"
        elif "StartCalendarInterval" in data:
            cal  = data["StartCalendarInterval"]
            h, m = cal.get("Hour", 0), cal.get("Minute", 0)
            if "Weekday" in cal:
                days     = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                when_str = f"{days[cal['Weekday']]} {h:02d}:{m:02d}"
            elif "Day" in cal:
                when_str = f"monthly/{cal['Day']} {h:02d}:{m:02d}"
            else:
                when_str = f"daily {h:02d}:{m:02d}"
        else:
            when_str = "?"

        log_out, _ = _log_paths(name)
        results.append({
            "name":   name,
            "label":  lbl,
            "plist":  str(path),
            "when":   when_str,
            "loaded": _is_loaded(lbl),
            "log":    log_out,
        })

    return results


def show_schedules() -> None:
    """Render all registered scheduled scans in a Rich table."""
    schedules = list_schedules()
    if not schedules:
        console.print(
            "[muted]No schedules yet. Use:[/muted] [accent]bee schedule add <name>[/accent]"
        )
        return

    t = Table(
        title="📅 Scheduled Scans",
        box=box.DOUBLE_EDGE,
        title_style="primary",
        header_style="accent",
    )
    t.add_column("Name",   style="bold white")
    t.add_column("When",   style="info")
    t.add_column("Loaded", justify="center")
    t.add_column("Plist",  style="muted", no_wrap=True)
    t.add_column("Log",    style="muted", no_wrap=True)

    for s in schedules:
        loaded_cell = "[success]●[/success]" if s["loaded"] else "[danger]○[/danger]"
        t.add_row(
            s["name"], s["when"], loaded_cell,
            Path(s["plist"]).name, Path(s["log"]).name,
        )

    console.print(t)


def remove_schedule(name: str) -> bool:
    """Unload and delete a scheduled scan job by name."""
    lbl   = _label(name)
    plist = _plist_path(name)

    if not plist.exists():
        console.print(f"[danger]❌ Schedule '{name}' not found.[/danger]")
        return False

    if IS_MACOS and _is_loaded(lbl):
        subprocess.run(["launchctl", "unload", str(plist)],
                       capture_output=True, text=True)

    plist.unlink(missing_ok=True)
    console.print(f"[success]✅ Schedule '{name}' removed.[/success]")
    return True


def enable_schedule(name: str) -> bool:
    """Load (re-enable) a launchd schedule without recreating the plist."""
    if not IS_MACOS:
        console.print("[warning]⚠ enable/disable is only available on macOS.[/warning]")
        return False

    plist = _plist_path(name)
    if not plist.exists():
        console.print(f"[danger]❌ Schedule '{name}' not found.[/danger]")
        return False

    res = subprocess.run(["launchctl", "load", "-w", str(plist)],
                         capture_output=True, text=True)
    if res.returncode == 0:
        console.print(f"[success]✅ Schedule '{name}' enabled.[/success]")
        return True

    console.print(f"[danger]❌ {res.stderr.strip()}[/danger]")
    return False


def disable_schedule(name: str) -> bool:
    """Unload (disable) a launchd schedule without deleting the plist."""
    if not IS_MACOS:
        console.print("[warning]⚠ enable/disable is only available on macOS.[/warning]")
        return False

    lbl   = _label(name)
    plist = _plist_path(name)

    if not plist.exists():
        console.print(f"[danger]❌ Schedule '{name}' not found.[/danger]")
        return False

    if not _is_loaded(lbl):
        console.print(f"[warning]Schedule '{name}' is already not loaded.[/warning]")
        return True

    res = subprocess.run(["launchctl", "unload", "-w", str(plist)],
                         capture_output=True, text=True)
    if res.returncode == 0:
        console.print(f"[success]✅ Schedule '{name}' disabled.[/success]")
        return True

    console.print(f"[danger]❌ {res.stderr.strip()}[/danger]")
    return False


def run_now(name: str) -> bool:
    """Trigger a scheduled scan immediately, outside its normal schedule."""
    lbl   = _label(name)
    plist = _plist_path(name)

    if not plist.exists():
        console.print(f"[danger]❌ Schedule '{name}' not found.[/danger]")
        return False

    if IS_MACOS:
        if not _is_loaded(lbl):
            subprocess.run(["launchctl", "load", "-w", str(plist)],
                           capture_output=True, text=True)

        res = subprocess.run(["launchctl", "start", lbl],
                              capture_output=True, text=True)
        if res.returncode == 0:
            console.print(f"[success]✅ '{name}' triggered via launchctl.[/success]")
            return True

        console.print(
            f"[warning]⚠ launchctl start: {res.stderr.strip()}\n"
            "Falling back to direct invocation…[/warning]"
        )

    return _run_direct(name, plist)


def show_logs(name: str, lines: int = 50) -> None:
    """
    Print the tail of a schedule's stdout log file with line numbers,
    rendered inside a Rich panel.
    """
    log_out, _ = _log_paths(name)
    log_path   = Path(log_out)

    if not log_path.exists():
        console.print(f"[muted]No log file yet for '{name}':[/muted] {log_out}")
        return

    all_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    start_idx = max(0, len(all_lines) - lines)
    tail      = all_lines[start_idx:]

    numbered = "\n".join(
        f"[dim]{start_idx + i + 1:5d}[/dim]  {ln}"
        for i, ln in enumerate(tail)
    )
    console.print(Panel(
        numbered or "[muted](empty)[/muted]",
        title=f"[accent]📋 Logs — {name} (last {len(tail)} lines)[/accent]",
        border_style="accent",
        expand=False,
    ))


# ── direct-run fallback ───────────────────────────────────────────────────────

def _run_direct(name: str, plist: Path) -> bool:
    """
    Parse ProgramArguments from the plist and invoke bee scan directly.
    Used as a fallback when launchctl is unavailable or fails.
    """
    try:
        with open(plist, "rb") as fh:
            data = plistlib.load(fh)
        args = data.get("ProgramArguments", [])
        if not args:
            console.print("[danger]❌ No ProgramArguments found in plist.[/danger]")
            return False
        env = {**os.environ, **data.get("EnvironmentVariables", {})}
        res = subprocess.run(args, env=env, text=True)
        return res.returncode == 0
    except Exception as exc:
        console.print(f"[danger]❌ Direct run failed:[/danger] {exc}")
        return False
