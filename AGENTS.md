# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AudioFiles is a single-file PySide6 (Qt6) desktop application for batch-renaming audio files using embedded metadata tags and optionally embedding cover art. The entire application lives in `audiofiles.py` (~500 lines). It supports MP3, FLAC, M4A, WAV, and OGG formats.

## Commands

```bash
# Run the application (uses PEP 723 inline script metadata)
./audiofiles.py

# Lint
ruff check audiofiles.py

# Format
ruff format audiofiles.py

# Build standalone executable (auto-detects OS and arch)
./build.sh

# Override platform on WSL to build a Linux binary instead of Windows
BUILD_TARGET=linux ./build.sh
```

## Build Script

`build.sh` uses PyInstaller to produce a distributable executable. It auto-detects the OS (macOS, Linux, Windows/MSYS2, WSL) and architecture (arm64, amd64).

- **macOS** — `--onedir` + `--windowed` produces an `AudioFiles.app` bundle
- **Windows** — `--onefile` + `--windowed` produces `AudioFiles.exe`
- **Linux** — `--onefile` produces an `AudioFiles` binary
- **WSL** — defaults to a Windows build; override with `BUILD_TARGET=linux`

Set `BUILD_TARGET` env var (`linux`, `macos`, `windows`) to override platform detection.

## Architecture

The app is a single Python file with two classes:

- **`DraggableFieldList(QListWidget)`** — Custom drag-to-reorder list widget for configuring which metadata fields appear in renamed filenames and their order.
- **`AudioRenamer(QMainWindow)`** — Main application window handling file loading (drag-and-drop or menu), metadata extraction via `mutagen`, rename preview with conflict detection, batch renaming, cover art embedding via `Pillow`, and optional metadata sync.

**Processing flow:** Load files → extract metadata → sort by (disc, track) → generate filenames from selected/ordered fields → preview in table (red rows = conflicts) → rename + embed cover + update metadata.

**Cover art embedding** is supported for MP3 (ID3 APIC frames) and FLAC (Vorbis picture blocks) only.

## Code Style

- **Ruff** for linting and formatting: line length 130, target Python 3.13
- Enabled rule sets: E, F, UP, B, SIM, I (pycodestyle, pyflakes, pyupgrade, flake8-bugbear, flake8-simplify, isort)
- Max cyclomatic complexity: 10
- 4-space indentation, LF line endings

## Tooling

- **Python 3.13** managed via mise (`.tool-versions`)
- **uv** for dependency management and script execution
- Dependencies are declared both in `pyproject.toml` and as PEP 723 inline script metadata in `audiofiles.py`
