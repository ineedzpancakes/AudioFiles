# AudioFiles

A desktop application for batch-renaming and organizing audio files using their embedded metadata tags. Built with Python and PySide6, and designed for use with the **Snowsky Echo Mini** music player and other Snowsky devices.

<img width="1006" height="837" alt="Screenshot_20260304_104400" src="https://github.com/user-attachments/assets/f019142d-10fd-4b27-90d7-4c1accdc38af" />

Full Disclosure: Made with Claude and therefore AI slop. I'll rewrite this in C++ one day.
---

## Features

- **Batch rename** audio files based on embedded metadata — track number, disc number, artist, album, and title
- **Live rename preview** — see original and new filenames side by side before committing any changes
- **Conflict detection** — rows highlighted in red when a rename would overwrite an existing file
- **Multi-disc support** — automatically detects multi-disc albums and handles sequential track numbering correctly
- **Cover art replacement** — embed a new cover image into MP3 and FLAC files, with configurable output dimensions and aspect ratio preservation
- **Metadata sync** — optionally rewrite the file's tags to match your rename selections
- **Flexible file loading** — drag and drop files or folders, or use **File > Open File / Open Folder** from the menu bar
- **Recursive folder scanning** — automatically finds all supported audio files within subdirectories

---

## Supported Formats

| Format | Rename | Cover Art |
|--------|--------|-----------|
| `.mp3` | ✅ | ✅ |
| `.flac` | ✅ | ✅ |
| `.m4a` | ✅ | — |
| `.wav` | ✅ | — |
| `.ogg` | ✅ | — |

---

## Installation

### Option 1 — Download a prebuilt release (Recommended)

Head to the [Releases](../../releases) page and download the executable for your platform:

- `AudioFiles-Windows.exe` — Windows
- `AudioFiles-MacOS.dmg` — macOS
- `AudioFiles-Linux` — Linux

No Python installation required.

### Option 2 — Run from source

**Requirements:** Python 3.9+

```bash
# Clone the repository
git clone https://github.com/your-username/audiofiles.git
cd audiofiles

# Install dependencies
pip install PySide6 mutagen Pillow

# Run the app
python audiofiles.py
```

---

## Usage

1. **Load your files** — drag and drop audio files or a folder onto the window, or use **File > Open File...** (`Ctrl+O`) / **File > Open Folder...** (`Ctrl+Shift+O`)
2. **Choose rename options** — check the fields you want included in the filename (track number and title are on by default)
3. **Preview the changes** — the table shows original and new filenames in real time; red rows indicate naming conflicts
4. **Optionally replace cover art** — check *Replace Cover Art*, upload an image, and set your desired output size
5. **Optionally sync metadata** — check *Update Metadata to Match Rename* to rewrite the file tags to match your selections (**this cannot be undone**)
6. **Click Rename Files** — a progress bar will track the operation; a summary dialog confirms how many files were processed

---

## Building from Source

This project uses [PyInstaller](https://pyinstaller.org/) to produce standalone executables. You must build on the target platform.

```bash
pip install pyinstaller

pyinstaller --onefile --windowed --hidden-import=mutagen --hidden-import=PIL --name "AudioFiles" audiofiles.py
```

The output executable will be in the `dist/` folder.

> **Note for macOS:** use `--onedir` instead of `--onefile` for a proper `.app` bundle.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| [PySide6](https://pypi.org/project/PySide6/) | GUI framework (Qt6 bindings) |
| [mutagen](https://pypi.org/project/mutagen/) | Audio metadata reading and writing |
| [Pillow](https://pypi.org/project/Pillow/) | Cover image processing and resizing |

---

## Contributing
---

Go crazy.

---
