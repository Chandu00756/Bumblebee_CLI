"""Rich theme, banners, and shared visual helpers."""
from rich.theme import Theme
from rich.console import Console
from rich.text import Text
from rich import box
from rich.panel import Panel
from bbcli import __version__ as _ver

THEME = Theme({
    "primary":     "bold #FFD700",
    "accent":      "bold #FFA500",
    "success":     "bold #00FF87",
    "danger":      "bold #FF4F4F",
    "warning":     "bold #FFB347",
    "muted":       "dim #A8A8A8",
    "info":        "bold #5BC0EB",
    "header":      "bold #FFD700 on #1A1A2E",
    "subtle":      "dim white",
    "critical":    "bold white on #FF4F4F",
    "high":        "bold #FF4F4F",
    "medium":      "bold #FFB347",
    "low":         "bold #FFD700",
    "clean":       "bold #00FF87",
    "ecosystem.npm":              "#F7DF1E",
    "ecosystem.pypi":             "#3776AB",
    "ecosystem.go":               "#00ADD8",
    "ecosystem.rubygems":         "#CC0000",
    "ecosystem.packagist":        "#8892BF",
    "ecosystem.mcp":              "#A855F7",
    "ecosystem.editor-extension": "#007ACC",
    "ecosystem.browser-extension":"#FF6D00",
})

console = Console(theme=THEME, highlight=False)

BANNER = """[primary]
  ██████╗ ██╗   ██╗███╗   ███╗██████╗ ██╗     ███████╗██████╗ ███████╗███████╗
  ██╔══██╗██║   ██║████╗ ████║██╔══██╗██║     ██╔════╝██╔══██╗██╔════╝██╔════╝
  ██████╔╝██║   ██║██╔████╔██║██████╔╝██║     █████╗  ██████╔╝█████╗  █████╗  
  ██╔══██╗██║   ██║██║╚██╔╝██║██╔══██╗██║     ██╔══╝  ██╔══██╗██╔══╝  ██╔══╝  
  ██████╔╝╚██████╔╝██║ ╚═╝ ██║██████╔╝███████╗███████╗██████╔╝███████╗███████╗
  ╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚═════╝ ╚══════╝╚══════╝╚═════╝ ╚══════╝╚══════╝
[/primary][accent]
  ╔══════════════════════════════════════════════════════════════════════════╗
  ║  🐝  Bumblebee CLI  •  Supply-Chain Security for macOS  •  v{_ver}      ║
  ║  🔍  Powered by Perplexity Bumblebee  •  Read-only  •  Zero side fx    ║
  ╚══════════════════════════════════════════════════════════════════════════╝
[/accent]"""

MINI_BANNER = f"[primary]🐝 Bumblebee CLI[/primary] [muted]v{_ver} — Dependency security scanner for macOS[/muted]"

ECOSYSTEM_COLORS = {
    "npm":               "ecosystem.npm",
    "pypi":              "ecosystem.pypi",
    "go":                "ecosystem.go",
    "rubygems":          "ecosystem.rubygems",
    "packagist":         "ecosystem.packagist",
    "mcp":               "ecosystem.mcp",
    "editor-extension":  "ecosystem.editor-extension",
    "browser-extension": "ecosystem.browser-extension",
}

SEVERITY_STYLES = {
    "critical": "critical",
    "high":     "high",
    "medium":   "medium",
    "low":      "low",
    "info":     "info",
}