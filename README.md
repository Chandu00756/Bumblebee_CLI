# 🐝 Bumblebee CLI

[![PyPI version](https://badge.fury.io/py/bumblebee-cli.svg)](https://pypi.org/project/bumblebee-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

**Dependency security scanner for macOS.** Detects malicious, vulnerable, and suspicious packages across npm, PyPI, Go, Ruby, and more — right from your terminal.

Type `bee` and you're scanning. No config files, no accounts, no setup beyond one install command.

Bumblebee CLI wraps the [Perplexity Bumblebee](https://github.com/perplexityai/bumblebee) scanner with a polished terminal interface — interactive REPL shell, auto-generated HTML/PDF reports, SBOM generation, scheduled background scans via launchd, and a live threat intelligence catalog system.

---

## Installation

### pip

```
pip install bumblebee-cli
```

Requires Python 3.11 or later. The `bee` command is available system-wide after install.

### Homebrew (macOS)

```
brew tap chanduchitikam/bumblebee
brew install bumblebee-cli
```

### From source

```
git clone https://github.com/Chandu00756/Bumblebee_CLI
cd Bumblebee_CLI
pip install .
```

---

## Quick start

```
bee
```

No arguments opens the interactive guided menu. Arrow keys to navigate, Enter to select.

---

## Step 1 — Install the scanner engine

Before scanning, install the Perplexity Bumblebee binary. Requires [Go](https://go.dev/dl/).

```
bee install
```

Verify:

```
bee selftest
```

---

## Commands

### Scan

```
bee scan /path/to/project
```

| Flag | Description |
|---|---|
| `--profile baseline\|deep\|fast` | Scan depth (default: baseline) |
| `--ecosystem npm` | Restrict to one or more ecosystems |
| `--findings-only` | Suppress clean packages, show only findings |
| `--output results.ndjson` | Save raw output to a file |
| `--max-duration 120` | Timeout in seconds |
| `--quiet` | Suppress progress output |

```
bee scan . --profile deep --findings-only
```

Quick scan — runs and saves a timestamped .ndjson file automatically:

```
bee quick .
```

---

### Reports

Generate an HTML or PDF report from a saved scan file:

```
bee report html results.ndjson
bee report pdf  results.ndjson
```

Generate from the most recent scan:

```
bee report last
bee report last --format pdf
```

Reports are saved to `~/.bumblebee-cli/reports/`.

---

### SBOM

Generate a Software Bill of Materials:

```
bee sbom                        # SPDX format (default)
bee sbom --format cyclonedx     # CycloneDX format
bee sbom --output my-sbom.json  # Custom output path
```

---

### Export

Export scan results in different formats:

```
bee export --format sarif   # GitHub Code Scanning compatible
bee export --format csv
bee export --format json
```

---

### CI / policy gate

Use in CI pipelines — exits non-zero if findings exceed the threshold:

```
bee ci .                        # Fail on any critical finding
bee ci . --fail-on high         # Fail on high or critical
bee ci . --fail-on none         # Always pass (report only)
```

---

### Diff

Compare two scan files to see what changed:

```
bee diff scan-before.ndjson scan-after.ndjson
```

---

### Threat scan

Deep scan against known threat intel advisories:

```
bee threat-scan
bee threat-scan my-catalog
```

---

### Scheduled scans

Bumblebee CLI uses macOS launchd to schedule recurring scans. No cron required.

```
bee schedule add morning-scan --when daily ~/
```

Available `--when` presets:

| Preset | Time |
|---|---|
| `morning` | 8:00 AM |
| `noon` | 12:00 PM |
| `daily` | 9:00 AM |
| `evening` | 6:00 PM |
| `night` | 10:00 PM |
| `weekly` | Monday 9:00 AM |
| `monthly` | 1st of month, 9:00 AM |
| `hourly` | Every 60 minutes |
| `HH:MM` | Specific time, e.g. `--when 14:30` |

Manage schedules:

```
bee schedule list
bee schedule enable   <name>
bee schedule disable  <name>
bee schedule run      <name>          # trigger immediately
bee schedule stop     <name>          # stop a running job
bee schedule logs     <name>          # tail stdout log
bee schedule delete-logs              # clear all log files
bee schedule delete-logs <name> --older-than 1w   # 1w | 2w | 1m | 2m | 3m | 6m | all
bee schedule remove   <name>
```

Use `bee schedule setup` for an interactive wizard with preset scenarios (full machine scan, nightly deep scan, threat intel watch, etc.).

---

### Exposure catalogs

Catalogs are JSON threat intelligence files used to match packages against known malicious indicators.

```
bee catalog list
bee catalog list-intel
bee catalog show    <catalog>
bee catalog create  <name>
bee catalog validate <file>
bee catalog fetch-intel
```

---

### History

```
bee history
bee history show
bee history last
bee history clear
```

---

### Installer management

```
bee install        # Install Bumblebee scanner binary
bee update         # Update to latest version
bee status         # Show installation path and version
bee selftest       # Run a quick sanity check
bee version        # Print bee version
```

---

### Interactive mode

```
bee
```

Starts a REPL-style shell with guided menus for all commands. Useful for exploratory scanning without memorising flags.

---

## Watching for changes

```
bee watch /path/to/project
```

Monitors the directory for file changes and re-scans automatically.

---

## Directory layout

All data stored under `~/.bumblebee-cli/`:

```
~/.bumblebee-cli/
    scans/       Raw .ndjson scan output files
    reports/     Generated HTML and PDF reports
    catalogs/    Exposure catalog JSON files
    history.json Scan history log
```

---

## Requirements

- macOS 12 or later (Monterey+)
- Python 3.11 or later
- Go 1.21 or later (required only for `bee install`)
- Internet access for initial binary installation and threat intel feeds

---

## License

MIT — see [LICENSE](LICENSE)

---

🐝 Powered by [Perplexity Bumblebee](https://github.com/perplexityai/bumblebee)
