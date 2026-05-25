# 🐝 Bumblebee CLI

A terminal-native supply-chain security scanner for macOS. Type `bee` and it opens. No configuration required to get started.

Bumblebee CLI wraps the [Perplexity Bumblebee](https://github.com/perplexityai/bumblebee) binary with a polished interface — interactive menus, scheduled scans via launchd, HTML and PDF reports, and a threat catalog system.

---

## Installation

### pip (recommended)

```
pip install bumblebee-cli
```

Requires Python 3.11 or later. After installation, the `bee` command is available system-wide.

### Homebrew (macOS)

```
brew tap chanduchitikam/bumblebee
brew install bumblebee-cli
```

### From source

```
git clone https://github.com/chanduchitikam/bumblebee-cli
cd bumblebee-cli
pip install .
```

---

## Quick start

```
bee
```

No arguments opens the interactive guided menu. Use the arrow keys to navigate and press Enter to select.

---

## Step 1 — Install the scanner

Before scanning, install the Perplexity Bumblebee binary. This requires [Go](https://go.dev/dl/) to be installed.

```
bee install
```

Verify it is working:

```
bee selftest
```

---

## Commands

### Scan

```
bee scan /path/to/project
```

Scan a specific directory. Options:

| Flag | Description |
|---|---|
| `--profile default` | Scan profile (default, strict, fast) |
| `--ecosystem npm` | Restrict to one or more ecosystems |
| `--findings-only` | Print only packages with findings, suppress clean ones |
| `--output results.ndjson` | Save raw NDJSON output to a file |
| `--max-duration 120` | Timeout in seconds |
| `--quiet` | Suppress progress output |

Example — scan current directory, strict profile, findings only:

```
bee scan . --profile strict --findings-only
```

---

### Reports

Generate an HTML or PDF report from a saved scan file.

```
bee report html results.ndjson
bee report pdf  results.ndjson
```

Reports are saved to `~/.bumblebee-cli/reports/`. Open the path printed in the terminal to view.

Generate a report from the most recent scan automatically:

```
bee report last --format html
```

---

### Scheduled scans

Bumblebee CLI uses macOS launchd to schedule recurring scans. No cron required.

Add a daily scan of your home directory at 9 AM:

```
bee schedule add morning-scan --when daily ~/
```

List all schedules:

```
bee schedule list
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
bee schedule disable morning-scan
bee schedule enable  morning-scan
bee schedule run-now morning-scan
bee schedule logs    morning-scan
bee schedule remove  morning-scan
```

---

### Exposure catalogs

Catalogs are JSON threat intelligence files that Bumblebee uses to match packages against known malicious indicators.

```
bee catalog list
bee catalog create my-catalog
bee catalog show  my-catalog
bee catalog validate my-catalog
```

Fetch a community threat intelligence feed:

```
bee catalog fetch-intel
```

---

### History

```
bee history
bee history clear
```

---

### Installer management

```
bee install          # Install Bumblebee binary
bee update           # Update to latest version
bee uninstall        # Remove Bumblebee binary
bee status           # Show installation status and version
bee version          # Print bee version
```

---

## Directory layout

All data is stored under `~/.bumblebee-cli/`:

```
~/.bumblebee-cli/
    scans/       Raw .ndjson scan output files
    reports/     Generated HTML and PDF reports
    catalogs/    Exposure catalog JSON files
    history.json Scan history log
```

---

## Publishing this package (how to put bee on PyPI)

The steps below turn this project into a package anyone can install with `pip install bumblebee-cli`.

### 1. Check PyPI for name availability

Open https://pypi.org/search/?q=bumblebee-cli and confirm the name is not taken.

### 2. Install build tools

```
pip install build twine
```

### 3. Build the distribution

```
cd bumblebee-cli
python -m build
```

This creates two files in `dist/`:
- `bumblebee_cli-1.1.0.tar.gz` — source distribution
- `bumblebee_cli-1.1.0-py3-none-any.whl` — wheel

### 4. Create a PyPI account

Register at https://pypi.org/account/register/ and enable two-factor authentication.

### 5. Create an API token

Go to https://pypi.org/manage/account/token/ and create a token scoped to the project.

### 6. Upload

```
twine upload dist/*
```

Enter `__token__` as the username and your API token as the password.

After this, anyone can install your package:

```
pip install bumblebee-cli
```

And type `bee` to launch it.

### 7. Publish to Homebrew (macOS)

Create a GitHub repository named `homebrew-bumblebee`. Inside it, add a file named `bumblebee-cli.rb`:

```ruby
class BumblebeeCli < Formula
  include Language::Python::Virtualenv

  desc "Supply-chain security scanner CLI for macOS"
  homepage "https://github.com/chanduchitikam/bumblebee-cli"
  url "https://files.pythonhosted.org/packages/.../bumblebee_cli-1.1.0.tar.gz"
  sha256 "REPLACE_WITH_SHA256_FROM_PyPI"
  license "MIT"

  depends_on "python@3.12"
  depends_on "go" => :build

  resource "rich" do
    url "https://files.pythonhosted.org/packages/.../rich-13.7.0.tar.gz"
    sha256 "..."
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/bee", "version"
  end
end
```

Users then install with:

```
brew tap chanduchitikam/bumblebee
brew install bumblebee-cli
```

---

## Requirements

- macOS 12 or later (Monterey+)
- Python 3.11 or later
- Go 1.21 or later (only needed for `bee install`)
- Internet access for initial binary installation and threat intel feeds

---

## License

MIT — see [LICENSE](LICENSE)

---

🐝 Powered by [Perplexity Bumblebee](https://github.com/perplexityai/bumblebee)
- **History** track every action you take
- **Scheduler** set up recurring scan tasks
- **Interactive mode** a REPL-style shell for exploratory use

## Installation

```bash
pip install -e .
```

Or install dependencies directly:

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Show help
bbcli --help

# Install a package
bbcli install requests

# Install a specific version
bbcli install requests --version 2.28.0

# Uninstall a package
bbcli uninstall requests

# List installed packages
bbcli list

# Scan a directory
bbcli scan-cmd --target ./my-project

# Generate a report
bbcli report --format json --output report.json

# Browse the catalog
bbcli catalog

# Show history
bbcli history --limit 10

# Start interactive mode
bbcli interactive
```

## Development

### Setup

```bash
git clone https://github.com/your-org/Bumblebee_CLI.git
cd Bumblebee_CLI
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Running Tests

```bash
pytest tests/ -v --cov=bbcli
```

## Project Structure

```
Bumblebee_CLI/
├── bbcli/
│   ├── __init__.py       # Package metadata
│   ├── main.py           # CLI entry point (Click commands)
│   ├── theme.py          # Rich console theme & helpers
│   ├── installer.py      # Package install/uninstall logic
│   ├── scanner.py        # Dependency & project scanner
│   ├── scheduler.py      # Task scheduler
│   ├── reporter.py       # Report generation (text/json/html)
│   ├── catalog.py        # Curated package catalog
│   ├── history.py        # Action history tracking
│   └── interactive.py    # Interactive REPL mode
├── tests/
│   ├── __init__.py
│   ├── test_installer.py
│   ├── test_scanner.py
│   ├── test_reporter.py
│   ├── test_catalog.py
│   └── test_history.py
├── requirements.txt
├── setup.py
└── README.md
```

## License

MIT
