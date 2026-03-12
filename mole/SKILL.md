---
name: "mole"
description: "Deep clean, optimize, and analyze your Mac using Mole (mo CLI)"
enabled: true
trigger: manual
---

# Mole Skill

Deep clean and optimize macOS using the `mo` CLI tool. Combines CleanMyMac, AppCleaner, DaisyDisk, and iStat Menus into a single binary.

## Requirements
- macOS
- `mo` installed via `brew install mole` or install script

## When to use
- User wants to clean up disk space, caches, logs, browser leftovers
- User wants to uninstall apps thoroughly (with leftover files)
- User wants to optimize/refresh system services and caches
- User wants to analyze disk usage visually
- User wants to check live system health (CPU, memory, disk, network)
- User wants to clean project build artifacts (node_modules, target, etc.)
- User wants to find and remove installer files (.dmg, .pkg)

## How to execute

### Interactive Menu
```bash
mo
```

### Deep System Cleanup
```bash
# Preview what will be cleaned (ALWAYS do this first)
mo clean --dry-run

# Preview with detailed risk levels and file info
mo clean --dry-run --debug

# Actually run the cleanup
mo clean

# Manage protected caches (whitelist)
mo clean --whitelist
```

### Smart App Uninstaller
```bash
# Interactive app removal with leftover detection
mo uninstall
```
Removes: app binary, Application Support, Caches, Preferences, Logs, WebKit storage, Cookies, Extensions, Plugins, Launch daemons, diagnostic reports.

### System Optimization
```bash
# Preview optimization actions
mo optimize --dry-run

# Run optimization (rebuilds databases, resets network, refreshes Finder/Dock, etc.)
mo optimize

# Detailed operation logs
mo optimize --debug

# Manage protected optimization rules
mo optimize --whitelist
```

### Disk Space Analyzer
```bash
# Analyze home directory
mo analyze

# Analyze external drives
mo analyze /Volumes
```
Supports arrow keys and Vim bindings (h/j/k/l). Press O to open, F to show in Finder, Backspace to delete, L for large files, Q to quit.

### Live System Status
```bash
# Real-time dashboard: CPU, GPU, memory, disk, network, power
mo status
```
Shows health score (color-coded), hardware info, and performance metrics. Press k to toggle cat, q to quit.

### Project Artifact Purge
```bash
# Clean build artifacts (node_modules, target, build, dist, venv, etc.)
mo purge

# Configure project scan directories
mo purge --paths
```
Recent projects (<7 days) are marked and unselected by default.

### Installer Cleanup
```bash
# Find and remove .dmg, .pkg, .zip installers
mo installer
```
Scans Downloads, Desktop, Homebrew caches, iCloud, and Mail.

### Utility Commands
```bash
# Configure Touch ID for sudo
mo touchid

# Set up shell tab completion
mo completion

# Update Mole
mo update

# View operation logs
mo log

# Remove Mole from system
mo remove

# Show help
mo --help

# Show version
mo --version
```

## Safety Notes
- **ALWAYS preview with `--dry-run` before running clean or optimize**
- File deletion is permanent - review operations carefully
- Built with strict protections - see `SECURITY_AUDIT.md`
- Operations logged to `~/.config/mole/operations.log` (disable with `MO_NO_OPLOG=1`)
- Use `--debug` for detailed logs, combine with `--dry-run` for comprehensive preview

## Terminal Compatibility
- Recommended: Alacritty, Kitty, WezTerm, Ghostty, Warp
- iTerm2 has known compatibility issues
- Override terminal detection: `MO_LAUNCHER_APP=<name>`

## GitHub
- Repository: https://github.com/tw93/Mole
- License: MIT