"""
Reporter module for Bumblebee CLI.

Parses Bumblebee NDJSON scan output and generates dark-themed HTML and PDF
security reports with KPI cards, ecosystem breakdowns, findings tables,
diagnostics, and package inventories.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bbcli.theme import console

# ── output directory ──────────────────────────────────────────────────────────
REPORT_DIR = Path.home() / ".bumblebee-cli" / "reports"


# ── colour maps ───────────────────────────────────────────────────────────────

# CSS colours (for HTML) — (background, foreground) per severity
_SEV_CSS: dict[str, tuple[str, str]] = {
    "critical": ("#FF4F4F", "#000"),
    "high":     ("#FF8C42", "#000"),
    "medium":   ("#FFD700", "#000"),
    "low":      ("#7EB8F7", "#000"),
    "info":     ("#A8A8A8", "#000"),
}

_ECO_CSS: dict[str, str] = {
    "npm":               "#F7DF1E",
    "pypi":              "#3776AB",
    "go":                "#00ADD8",
    "rubygems":          "#CC0000",
    "packagist":         "#8892BF",
    "mcp":               "#A855F7",
    "editor-extension":  "#007ACC",
    "browser-extension": "#FF6D00",
}

_CONF_CSS: dict[str, str] = {
    "high":   "var(--success)",
    "medium": "var(--gold)",
    "low":    "var(--danger)",
}

# RGB tuples for fpdf2 — mirror the CSS values above


def _pdf_safe(text: str) -> str:
    """Replace characters outside Latin-1 with ASCII equivalents.

    fpdf2 built-in fonts (Helvetica / Times / Courier) only support Latin-1
    (U+0000-U+00FF).  Any character outside that range raises an error.
    This helper replaces the most common offenders and drops the rest.
    """
    _MAP = {
        "\u2013": "-",   # en-dash
        "\u2014": "-",   # em-dash
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2026": "...", # ellipsis
        "\u00b7": ".",   # middle dot
        "\u2022": "*",   # bullet
        "\u2192": "->",  # right arrow
        "\u00a0": " ",   # non-breaking space
        "\u2713": "OK",  # check mark
        "\u2714": "OK",  # heavy check mark
        "\u2717": "X",   # ballot x
        "\u2718": "X",   # heavy ballot x
        "\u00d7": "x",   # multiplication sign
    }
    result = []
    for ch in text:
        if ch in _MAP:
            result.append(_MAP[ch])
        elif ord(ch) > 0x00FF:
            import unicodedata
            norm = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode()
            result.append(norm or "?")
        else:
            result.append(ch)
    return "".join(result)


_SEV_RGB: dict[str, tuple[int, int, int]] = {
    "critical": (185, 28,  28),   # dark red
    "high":     (194, 65,   0),   # dark orange
    "medium":   (146, 100,  0),   # dark amber
    "low":      (  2,  96, 170),  # dark blue
    "info":     ( 90,  90,  90),  # dark gray
}

_ECO_RGB: dict[str, tuple[int, int, int]] = {
    "npm":               (150, 120,   0),  # dark gold
    "pypi":              (  0,  80, 150),  # dark blue
    "go":                (  0, 130, 160),  # dark teal
    "rubygems":          (160,  0,    0),  # dark red
    "packagist":         ( 80,  80, 160),  # dark purple
    "mcp":               (110,  50, 170),  # dark violet
    "editor-extension":  (  0,  80, 175),  # dark azure
    "browser-extension": (170,  55,   0),  # dark orange
}

_CONF_RGB: dict[str, tuple[int, int, int]] = {
    "high":   (  0, 130,  60),  # dark green
    "medium": (146, 100,   0),  # dark amber
    "low":    (185,  28,  28),  # dark red
}


# ── NDJSON parser ─────────────────────────────────────────────────────────────

def _parse_ndjson(ndjson_path: str) -> dict:
    """Read a Bumblebee NDJSON file and categorise every record by record_type."""
    packages:    list = []
    findings:    list = []
    diagnostics: list = []
    summary:     dict = {}

    with open(ndjson_path, "r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
                rt  = rec.get("record_type", "")
                if rt == "package":
                    packages.append(rec)
                elif rt == "finding":
                    findings.append(rec)
                elif rt == "scan_summary":
                    summary = rec
                elif rt == "diagnostic":
                    diagnostics.append(rec)
            except json.JSONDecodeError:
                pass

    ecosystems: dict[str, int] = {}
    for p in packages:
        eco = p.get("ecosystem", "unknown")
        ecosystems[eco] = ecosystems.get(eco, 0) + 1

    return {
        "packages":    packages,
        "findings":    findings,
        "diagnostics": diagnostics,
        "summary":     summary,
        "ecosystems":  ecosystems,
    }


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _kpi_card(label: str, value: str,
              color: str = "var(--gold)", sub: str = "") -> str:
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="kpi">' +
        f'<div class="kpi-val" style="color:{color}">{value}</div>' +
        f'<div class="kpi-label">{label}</div>' +
        sub_html +
        "</div>"
    )


def _eco_breakdown_rows(ecosystems: dict[str, int]) -> str:
    if not ecosystems:
        return '<tr><td colspan="3" class="empty">No packages found</td></tr>'
    total = sum(ecosystems.values()) or 1
    rows  = ""
    for eco, cnt in sorted(ecosystems.items(), key=lambda x: -x[1]):
        pct   = cnt / total * 100
        color = _ECO_CSS.get(eco, "#888")
        bar   = (
            '<div class="bar-track">' +
            f'<div class="bar-fill" style="width:{pct:.1f}%;background:{color}"></div>' +
            "</div>"
        )
        rows += (
            "<tr>" +
            f'<td style="color:{color};font-weight:700">{eco}</td>' +
            f'<td style="text-align:right">{cnt:,}</td>' +
            f'<td class="bar-cell">{bar} <span class="muted">{pct:.1f}%</span></td>' +
            "</tr>"
        )
    return rows


def _findings_rows(findings: list) -> str:
    if not findings:
        return (
            '<tr><td colspan="6" class="clean-cell">' +
            "\u2705 No findings detected — machine looks clean!" +
            "</td></tr>"
        )
    rows = ""
    for f in findings:
        sev    = f.get("severity", "info").lower()
        bg, fg = _SEV_CSS.get(sev, ("#888", "#000"))
        eco    = f.get("ecosystem", "")
        eco_c  = _ECO_CSS.get(eco, "#888")
        rows += (
            "<tr>" +
            f'<td><span class="badge" style="background:{bg};color:{fg}">' +
            f"{sev.upper()}</span></td>" +
            f'<td class="pkg-name">{f.get("package_name", "")}</td>' +
            f'<td style="color:var(--orange)">{f.get("version", "")}</td>' +
            f'<td style="color:{eco_c}">{eco}</td>' +
            f'<td style="color:var(--blue)">' +
            f'{f.get("catalog_name", f.get("catalog_id", ""))}</td>' +
            f'<td class="evidence">{f.get("evidence", "")}</td>' +
            "</tr>"
        )
    return rows


def _diagnostics_rows(diagnostics: list) -> str:
    if not diagnostics:
        return '<tr><td colspan="3" class="empty">No diagnostics</td></tr>'
    rows = ""
    for d in diagnostics:
        level = d.get("level", "info")
        color = {
            "error":   "var(--danger)",
            "warning": "var(--orange)",
        }.get(level, "var(--muted)")
        rows += (
            "<tr>" +
            f'<td style="color:{color}">{level}</td>' +
            f'<td>{d.get("message", "")}</td>' +
            f'<td class="evidence">{d.get("detail", "")}</td>' +
            "</tr>"
        )
    return rows


def _package_rows(packages: list, limit: int = 300) -> str:
    rows = ""
    for p in packages[:limit]:
        eco   = p.get("ecosystem", "")
        eco_c = _ECO_CSS.get(eco, "#888")
        conf  = p.get("confidence", "")
        conf_c = _CONF_CSS.get(conf, "var(--muted)")
        src   = Path(p.get("source_file", "")).name
        rows += (
            "<tr>" +
            f'<td style="color:{eco_c}">{eco}</td>' +
            f'<td class="pkg-name">{p.get("package_name", "")}</td>' +
            f'<td style="color:var(--orange)">{p.get("version", "")}</td>' +
            f'<td style="color:{conf_c}">{conf}</td>' +
            f'<td class="evidence">{src}</td>' +
            "</tr>"
        )
    return rows


# CSS using custom properties on #0d1117 background with gold accents
_HTML_CSS = """
    :root {
      --bg:      #0d1117;
      --surface: #161b22;
      --border:  #30363d;
      --text:    #c9d1d9;
      --muted:   #8b949e;
      --gold:    #FFD700;
      --orange:  #FFA500;
      --success: #00FF87;
      --danger:  #FF4F4F;
      --blue:    #5BC0EB;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg); color: var(--text);
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      font-size: 14px; padding: 32px 40px; line-height: 1.5;
    }
    h1 { color: var(--gold); font-size: 26px; margin-bottom: 4px; }
    h2 { color: var(--orange); font-size: 15px; font-weight: 600;
         margin: 28px 0 12px; padding-bottom: 6px;
         border-bottom: 1px solid var(--border); }
    .subtitle { color: var(--muted); font-size: 12px; margin-bottom: 28px; }
    .kpi-row  { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 28px; }
    .kpi {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 8px; padding: 14px 22px; min-width: 120px; text-align: center;
    }
    .kpi-val   { font-size: 26px; font-weight: 700; color: var(--gold); }
    .kpi-label { font-size: 10px; color: var(--muted); margin-top: 4px;
                 text-transform: uppercase; letter-spacing: 0.6px; }
    .kpi-sub   { font-size: 10px; color: var(--muted); margin-top: 2px; }
    .section {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 8px; padding: 20px; margin-bottom: 20px; overflow-x: auto;
    }
    table  { width: 100%; border-collapse: collapse; }
    th {
      background: #1f2430; color: var(--gold); padding: 9px 12px;
      text-align: left; font-size: 11px; text-transform: uppercase;
      letter-spacing: 0.5px; white-space: nowrap;
    }
    td { padding: 7px 12px; border-bottom: 1px solid var(--border); color: var(--text); }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #1f2430; }
    .badge {
      display: inline-block; padding: 2px 8px; border-radius: 4px;
      font-weight: 700; font-size: 10px; letter-spacing: 0.5px;
    }
    .pkg-name  { font-weight: 600; }
    .evidence  { color: var(--muted); font-size: 12px; }
    .muted     { color: var(--muted); font-size: 11px; }
    .empty     { color: var(--muted); text-align: center; padding: 14px; font-style: italic; }
    .clean-cell {
      color: var(--success); text-align: center; padding: 18px;
      font-size: 15px; font-weight: 600;
    }
    .bar-track {
      display: inline-block; background: var(--border); border-radius: 4px;
      height: 12px; width: 120px; vertical-align: middle; overflow: hidden; margin-right: 6px;
    }
    .bar-fill  { height: 12px; border-radius: 4px; }
    .bar-cell  { white-space: nowrap; }
    footer {
      color: var(--muted); font-size: 11px; margin-top: 40px;
      border-top: 1px solid var(--border); padding-top: 12px;
    }
"""


def generate_html(ndjson_path: str, output: Optional[str] = None) -> str:
    """
    Generate a dark-themed HTML security report from a Bumblebee NDJSON file.

    Sections:
      - Six KPI cards: files scanned, packages, findings, ecosystems,
        duplicates, diagnostics (with error count sub-label)
      - Ecosystem breakdown table with coloured visual bar charts
      - Security findings table (or a clean green ✅ box if none found)
      - Diagnostics section
      - Package inventory (first 300 packages)

    Args:
        ndjson_path: Path to the .ndjson scan output file.
        output:      Optional explicit destination path for the HTML file.

    Returns:
        Path to the generated HTML file, or "" on error.
    """
    if not os.path.exists(ndjson_path):
        console.print(f"[danger]\u274c File not found:[/danger] {ndjson_path}")
        return ""

    data        = _parse_ndjson(ndjson_path)
    packages    = data["packages"]
    findings    = data["findings"]
    diagnostics = data["diagnostics"]
    ecosystems  = data["ecosystems"]
    summary     = data["summary"]
    generated   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    src_name    = Path(ndjson_path).name

    fi_cnt   = len(findings)
    diag_err = len([d for d in diagnostics if d.get("level") == "error"])
    status_v = "\u2705 CLEAN" if not fi_cnt else f"\u26a0 {fi_cnt}"
    status_c = "var(--success)" if not fi_cnt else "var(--danger)"

    kpi_row = (
        _kpi_card("Files Scanned", f"{summary.get('files_considered', '\u2014')}")
        + _kpi_card("Packages",    f"{len(packages):,}")
        + _kpi_card("Findings",    status_v, status_c)
        + _kpi_card("Ecosystems",  str(len(ecosystems)))
        + _kpi_card("Duplicates",  str(summary.get("duplicates", 0)))
        + _kpi_card(
            "Diagnostics",
            str(len(diagnostics)),
            "var(--danger)" if diag_err else "var(--muted)",
            sub=f"{diag_err} error{'s' if diag_err != 1 else ''}" if diag_err else "",
        )
    )

    pkg_note = f"first {min(len(packages), 300):,} of {len(packages):,}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Bumblebee CLI \u2014 Security Report</title>
  <style>{_HTML_CSS}</style>
</head>
<body>
  <h1>\U0001f41d Bumblebee CLI \u2014 Security Report</h1>
  <p class="subtitle">
    Generated: {generated} &nbsp;|&nbsp; Source: {src_name} &nbsp;|&nbsp;
    Profile: {summary.get('profile', '\u2014')}
  </p>

  <div class="kpi-row">{kpi_row}</div>

  <div class="section">
    <h2>\U0001f4e6 Ecosystem Breakdown</h2>
    <table>
      <thead>
        <tr><th>Ecosystem</th><th style="text-align:right">Packages</th><th>Share</th></tr>
      </thead>
      <tbody>{_eco_breakdown_rows(ecosystems)}</tbody>
    </table>
  </div>

  <div class="section">
    <h2>\U0001f6a8 Security Findings ({len(findings)})</h2>
    <table>
      <thead>
        <tr>
          <th>Severity</th><th>Package</th><th>Version</th>
          <th>Ecosystem</th><th>Advisory</th><th>Evidence</th>
        </tr>
      </thead>
      <tbody>{_findings_rows(findings)}</tbody>
    </table>
  </div>

  <div class="section">
    <h2>\U0001f527 Diagnostics ({len(diagnostics)})</h2>
    <table>
      <thead><tr><th>Level</th><th>Message</th><th>Detail</th></tr></thead>
      <tbody>{_diagnostics_rows(diagnostics)}</tbody>
    </table>
  </div>

  <div class="section">
    <h2>\U0001f4cb Package Inventory ({pkg_note})</h2>
    <table>
      <thead>
        <tr>
          <th>Ecosystem</th><th>Package</th><th>Version</th>
          <th>Confidence</th><th>Source File</th>
        </tr>
      </thead>
      <tbody>{_package_rows(packages)}</tbody>
    </table>
  </div>

  <footer>
    Bumblebee CLI &nbsp;|&nbsp; Powered by Perplexity Bumblebee &nbsp;|&nbsp;
    Read-only scan \u2014 no code was executed &nbsp;|&nbsp; {generated}
  </footer>
</body>
</html>"""

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = output or str(REPORT_DIR / f"report_{_ts()}.html")
    Path(out).write_text(html, encoding="utf-8")
    console.print(f"[success]\u2705 HTML report:[/success] [accent]{out}[/accent]")
    return out


# ── PDF custom class ──────────────────────────────────────────────────────────

def _make_pdf_class():
    """Lazily import fpdf2 and return the branded BumblebeePDF class."""
    from fpdf import FPDF, XPos, YPos  # type: ignore[import]

    class BumblebeePDF(FPDF):
        _source_name: str = ""
        _generated:   str = ""

        def set_meta(self, source_name: str, generated: str) -> None:
            self._source_name = source_name
            self._generated   = generated

        def header(self) -> None:
            # Gold accent bar at top
            self.set_fill_color(220, 168, 0)
            self.rect(0, 0, 210, 2, style="F")
            # Title
            self.set_y(5)
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(26, 26, 26)
            self.cell(110, 7, _pdf_safe("Bumblebee CLI  Security Report"), align="L")
            # Right: filename + timestamp
            self.set_font("Helvetica", "", 7)
            self.set_text_color(130, 130, 130)
            self.set_y(5)
            self.cell(0, 7, _pdf_safe(f"{self._source_name}  |  {self._generated}"), align="R")
            # Hairline separator
            self.set_draw_color(210, 210, 210)
            self.set_y(13.5)
            self.cell(0, 0, "", border="B")
            self.ln(8)

        def footer(self) -> None:
            self.set_y(-11)
            self.set_draw_color(210, 210, 210)
            self.cell(0, 0, "", border="T")
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(160, 160, 160)
            self.cell(
                0, 5,
                _pdf_safe(f"Perplexity Bumblebee  |  Supply-chain Security for macOS  |  Page {self.page_no()}"),
                align="C",
            )

        def section_title(self, title: str) -> None:
            self.ln(4)
            y = self.get_y()
            # Left gold accent bar
            self.set_fill_color(220, 168, 0)
            self.rect(self.l_margin - 3, y, 2.5, 7, style="F")
            # Title cell with cream background
            self.set_fill_color(255, 251, 235)
            self.set_text_color(140, 95, 0)
            self.set_font("Helvetica", "B", 9)
            self.cell(
                0, 7, _pdf_safe("  " + title),
                fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT,
            )
            self.ln(1)

        def kv_row(self, key: str, val: str) -> None:
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(110, 110, 110)
            self.cell(50, 5.5, _pdf_safe(key))
            self.set_font("Helvetica", "", 8)
            self.set_text_color(26, 26, 26)
            self.cell(0, 5.5, _pdf_safe(val), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        def table_header(self, cols: list) -> None:
            self.set_fill_color(238, 238, 238)
            self.set_text_color(55, 55, 55)
            self.set_draw_color(200, 200, 200)
            self.set_font("Helvetica", "B", 7)
            for label, w in cols:
                self.cell(w, 6, _pdf_safe(label), fill=True, border=1)
            self.ln()

        def table_row(self, cells: list,
                      rgb: tuple = (26, 26, 26),
                      alt: bool = False) -> None:
            if alt:
                self.set_fill_color(248, 248, 248)
            self.set_draw_color(220, 220, 220)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*rgb)
            for text, w in cells:
                self.cell(w, 4.5, _pdf_safe(str(text)), border="B", fill=alt)
            self.ln()

    return BumblebeePDF, XPos, YPos


def generate_pdf(ndjson_path: str, output: Optional[str] = None) -> str:
    """
    Generate a multi-page PDF security report from a Bumblebee NDJSON file.

    Uses a custom BumblebeePDF class (fpdf2) with:
      - branded header (gold accent strip, filename, timestamp)
      - footer with page numbers
      - helper methods for section titles, key-value rows, table headers/rows
      - colour-coded severity, ecosystem, and confidence values
      - auto-paginating package inventory (new page every 200 rows)

    Args:
        ndjson_path: Path to the .ndjson scan output file.
        output:      Optional explicit destination path for the PDF file.

    Returns:
        Path to the generated PDF file, or "" on failure.
    """
    try:
        BumblebeePDF, XPos, YPos = _make_pdf_class()
    except ImportError:
        console.print("[danger]\u274c fpdf2 is required. Run:[/danger] [accent]pip install fpdf2[/accent]")
        return ""

    if not os.path.exists(ndjson_path):
        console.print(f"[danger]\u274c File not found:[/danger] {ndjson_path}")
        return ""

    data        = _parse_ndjson(ndjson_path)
    packages    = data["packages"]
    findings    = data["findings"]
    diagnostics = data["diagnostics"]
    ecosystems  = data["ecosystems"]
    summary     = data["summary"]
    generated   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    src_name    = Path(ndjson_path).name

    pdf = BumblebeePDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_meta(src_name, generated)
    pdf.add_page()

    # ── summary ───────────────────────────────────────────────────────────────
    pdf.section_title("Scan Summary")
    pdf.kv_row("Source file",   src_name)
    pdf.kv_row("Generated",     generated)
    pdf.kv_row("Profile",       summary.get("profile", "-"))
    pdf.kv_row("Files scanned", str(summary.get("files_considered", "-")))
    pdf.kv_row("Packages",      f"{len(packages):,}")
    pdf.kv_row("Findings",      str(len(findings)))
    pdf.kv_row("Ecosystems",    str(len(ecosystems)))
    pdf.kv_row("Duplicates",    str(summary.get("duplicates", 0)))
    pdf.kv_row("Diagnostics",   str(len(diagnostics)))
    pdf.ln(6)

    # ── ecosystem breakdown ───────────────────────────────────────────────────
    pdf.section_title("Ecosystem Breakdown")
    eco_cols = [("ECOSYSTEM", 50), ("PACKAGES", 25), ("BAR", 90), ("PCT", 25)]
    pdf.table_header(eco_cols)
    total_pkgs = sum(ecosystems.values()) or 1

    for eco, cnt in sorted(ecosystems.items(), key=lambda x: -x[1]):
        pct      = cnt / total_pkgs * 100
        r, g, b  = _ECO_RGB.get(eco, (136, 136, 136))
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(r, g, b)
        pdf.cell(50, 4.5, _pdf_safe(eco[:26]))
        pdf.set_text_color(26, 26, 26)
        pdf.cell(25, 4.5, str(cnt))
        # inline bar chart
        x0, y0  = pdf.get_x(), pdf.get_y()
        bar_px  = int(pct / 100 * 80)
        pdf.set_fill_color(r, g, b)
        pdf.rect(x0, y0 + 0.8, bar_px, 2.5, style="F")
        pdf.set_fill_color(225, 225, 225)
        if bar_px < 80:
            pdf.rect(x0 + bar_px, y0 + 0.8, 80 - bar_px, 2.5, style="F")
        pdf.set_xy(x0 + 90, y0)
        pdf.set_text_color(110, 110, 110)
        pdf.cell(25, 4.5, f"{pct:.0f}%")
        pdf.ln(4.5)
    pdf.ln(6)

    # ── findings ──────────────────────────────────────────────────────────────
    pdf.section_title(f"Security Findings ({len(findings)})")
    if not findings:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(0, 130, 60)
        pdf.cell(0, 6, "No findings detected - machine looks clean!",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        f_cols = [
            ("SEV", 16), ("PACKAGE", 46), ("VER", 18),
            ("ECO", 28), ("ADVISORY", 58), ("EVIDENCE", 24),
        ]
        pdf.table_header(f_cols)
        for f in findings:
            sev      = f.get("severity", "info").lower()
            sr, sg, sb = _SEV_RGB.get(sev, (168, 168, 168))
            er, eg, eb = _ECO_RGB.get(f.get("ecosystem", ""), (136, 136, 136))
            adv = f.get("catalog_name", f.get("catalog_id", ""))

            pdf.set_font("Helvetica", "B", 7)
            pdf.set_text_color(sr, sg, sb)
            pdf.cell(16, 4.5, sev[:4].upper())
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(26, 26, 26)
            pdf.cell(46, 4.5, _pdf_safe(f.get("package_name", "")[:26]))
            pdf.cell(18, 4.5, _pdf_safe(f.get("version", "")[:10]))
            pdf.set_text_color(er, eg, eb)
            pdf.cell(28, 4.5, _pdf_safe(f.get("ecosystem", "")[:14]))
            pdf.set_text_color(20, 100, 170)
            pdf.cell(58, 4.5, _pdf_safe(adv[:32]))
            pdf.set_text_color(110, 110, 110)
            pdf.cell(24, 4.5, _pdf_safe(f.get("evidence", "")[:14]))
            pdf.ln()
    pdf.ln(6)

    # ── diagnostics ───────────────────────────────────────────────────────────
    if diagnostics:
        pdf.section_title(f"Diagnostics ({len(diagnostics)})")
        d_cols = [("LEVEL", 20), ("MESSAGE", 100), ("DETAIL", 70)]
        pdf.table_header(d_cols)
        for d in diagnostics:
            level = d.get("level", "info")
            lr, lg, lb = {
                "error":   (255, 79,  79),
                "warning": (255, 165, 0),
            }.get(level, (168, 168, 168))
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(lr, lg, lb)
            pdf.cell(20, 4.5, _pdf_safe(level))
            pdf.set_text_color(26, 26, 26)
            pdf.cell(100, 4.5, _pdf_safe(d.get("message", "")[:56]))
            pdf.set_text_color(110, 110, 110)
            pdf.cell(70,  4.5, _pdf_safe(d.get("detail", "")[:40]))
            pdf.ln()
        pdf.ln(6)

    # ── package inventory (auto-paginate every 200 rows) ──────────────────────
    total_shown = min(len(packages), 200)
    pdf.section_title(f"Package Inventory (first {total_shown:,} of {len(packages):,})")
    p_cols = [
        ("ECOSYSTEM", 34), ("PACKAGE", 64), ("VERSION", 26),
        ("CONFIDENCE", 28), ("SOURCE", 38),
    ]
    pdf.table_header(p_cols)

    for i, p in enumerate(packages[:200]):
        if i > 0 and i % 200 == 0:
            pdf.add_page()
            pdf.section_title(f"Package Inventory (continued - rows {i + 1}+)")
            pdf.table_header(p_cols)

        eco      = p.get("ecosystem", "")
        er, eg, eb = _ECO_RGB.get(eco, (136, 136, 136))
        conf       = p.get("confidence", "")
        cr, cg, cb = _CONF_RGB.get(conf, (140, 140, 140))

        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(er, eg, eb)
        pdf.cell(34, 4.5, _pdf_safe(eco[:18]))
        pdf.set_text_color(26, 26, 26)
        pdf.cell(64, 4.5, _pdf_safe(p.get("package_name", "")[:34]))
        pdf.set_text_color(140, 95, 0)
        pdf.cell(26, 4.5, _pdf_safe(p.get("version", "")[:14]))
        pdf.set_text_color(cr, cg, cb)
        pdf.cell(28, 4.5, _pdf_safe(conf))
        pdf.set_text_color(110, 110, 110)
        pdf.cell(38, 4.5, _pdf_safe(Path(p.get("source_file", "")).name[:22]))
        pdf.ln()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = output or str(REPORT_DIR / f"report_{_ts()}.pdf")
    pdf.output(out)
    console.print(f"[success]\u2705 PDF report:[/success] [accent]{out}[/accent]")
    return out
