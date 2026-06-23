English | [简体中文](README.md)

# Muse

[![Download](https://img.shields.io/github/v/release/zjksstn/Muse?label=Download&color=blue)](https://github.com/zjksstn/Muse/releases/latest)

A local MP3 player built with Python (tkinter + pygame), featuring synced lyrics, album-art display, library management, metadata editing, and audio/video format conversion. It can also register itself as the system's default MP3 player.

> Formerly [sstnplayer](https://github.com/zjksstn/sstnplayer); renamed to Muse after a major rewrite.

## Download (prebuilt, no Python needed)

Grab a ready-to-run build from the [**Releases**](https://github.com/zjksstn/Muse/releases) page — two variants to choose from:

| Variant | File | Size | Best for |
|---|---|---|---|
| **Full** | `Muse_vX_win64.zip` | ~240 MB | Users who want lyric download (LDDC) and audio/video conversion (FFmpeg) bundled in |
| **Lite** | `Muse_Sim_vX_win64.zip` | ~19 MB | Users who just want clean playback with the smallest footprint |

Unzip, then double-click `muse.exe` (Lite: `muse_sim.exe`). **Keep the `.exe` together with the `_internal`, `images`, `config` (and `bin`, `LDDC` for Full) folders — don't move the exe out on its own.** Windows 64-bit only.

## Features

- **Local playback** — MP3 via `pygame.mixer`: play / pause / stop / previous / next / seek / mute
- **Synced lyrics** — parses `.lrc` files and highlights the current line as the song plays
- **Lyric download** — integrates [LDDC](https://github.com/chenmozhijin/LDDC) (external standalone tool) to search and fetch accurate lyrics
- **Album art** — automatically extracts and shows embedded MP3 cover art
- **Library management** — add/remove playlist entries, sort (by name / by time), save-as playlist, resume from last position
- **Metadata editing** — edit title / album / artist for one track or the whole library; batch-number titles and format filenames
- **Format conversion** — convert a single file or batch to MP3, extract the MP3 track from a video (requires FFmpeg)
- **System integration** — register Muse as the default handler for `.mp3` files

## Project layout

```
Muse/
├── muse.py        # main entry point
├── muse.spec      # PyInstaller build config
├── v2.ico         # app icon
├── images/        # UI icons / animation assets
├── config/        # config files, widget layout, playback history, etc.
├── bin/           # (provide yourself) FFmpeg executables
└── LDDC/          # (provide yourself) LDDC lyric tool
```

## Running from source

### Requirements

- Python 3.10+ (developed and packaged on 3.10)
- Windows (primary target; features such as `--register` file association are Windows-only)

```bash
pip install pygame pillow pyperclip selenium beautifulsoup4 requests eyed3 mutagen
python muse.py
```

> `selenium` needs a matching browser driver (e.g. ChromeDriver) installed and on your PATH.

### External tools (not bundled in the repo, download yourself)

These are large, independent third-party tools and are **not version-controlled in this repo**:

- **FFmpeg** (for conversion) — either [download FFmpeg](https://ffmpeg.org/download.html) and add it to your PATH (auto-detected), or drop `ffmpeg.exe` / `ffplay.exe` / `ffprobe.exe` into `bin/`. Without it, only the conversion buttons are affected.
- **LDDC** (for lyric download) — download the latest Windows build from [LDDC Releases](https://github.com/chenmozhijin/LDDC/releases), unzip, rename the folder to `LDDC`, and place it next to `muse.py` so that `LDDC/LDDC.exe` exists. Without it, only the lyric-download feature is affected.

> The prebuilt **Full** release on the Releases page already includes FFmpeg and LDDC, so you don't need to set these up manually.

## Building an executable

PyInstaller in `--onedir` mode (not splittable into a single file — see below). From the project root in PowerShell:

```powershell
# 1. Make sure PyInstaller is installed
.\.venv\Scripts\pip.exe show pyinstaller   # if missing: .\.venv\Scripts\pip.exe install pyinstaller

# 2. Build + copy resource folders (both steps required)
.\.venv\Scripts\pyinstaller.exe --onedir --noconsole --icon=v2.ico --noconfirm muse.py; foreach ($d in 'images','config','bin','LDDC') { Copy-Item $d "dist\muse\$d" -Recurse -Force }
```

The runnable program ends up in `F:\Muse\dist\muse\`. **When distributing or running, `muse.exe` must stay alongside `_internal`, `images`, `config`, `bin`, and `LDDC`** — never ship the exe alone.

| Flag | Meaning |
|---|---|
| `--onedir` | program folder (exe + `_internal`); not splittable |
| `--onefile` | single exe; slow startup, unpacks to a temp dir each run, config not persisted — **not recommended here** |
| `--noconsole` | hide the console window |
| `--noconfirm` | overwrite the old `dist` without asking |

**Why copy the resource folders separately:** the program reads `images/`, `config/`, `bin/`, `LDDC/` via relative paths, but `muse.spec` has `datas=[]` (doesn't bundle them) and PyInstaller's `COLLECT` step rebuilds `dist\muse\` each time — so they must be copied in afterward. The one-liner above already does this.

### Register as the default MP3 player

After building and copying resources, from `dist\muse\`:

```bash
.\muse.exe --register      # then: right-click any .mp3 → Open with → choose Muse → "Always"
.\muse.exe --unregister     # to undo
```

## Troubleshooting

1. **"Failed to load Python DLL ... python3XX.dll"** — you moved `muse.exe` away from its `_internal` folder. Keep the whole `dist\muse\` folder together.
2. **Crash on launch / can't find `widgets.json` or `v2.ico`** — resource folders weren't copied next to the exe; re-run the `Copy-Item` part.
3. **"FFmpeg not found" on convert/extract** — see *External tools → FFmpeg* above.
4. **Lyric download does nothing** — make sure `LDDC/LDDC.exe` exists; see *External tools → LDDC* above.

## License

TBD
