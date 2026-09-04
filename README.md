# VideoDownloaderPro

A professional and highly customizable video downloader relying on `yt-dlp` to download video and audio from various platforms such as YouTube and Instagram. It features a modern GUI built with `customtkinter`.

## Features

- Modern UI interface utilizing CustomTkinter (Dark and Light modes).
- Fast and reliable video downloading engine via `yt-dlp`.
- Options to download as:
  - Highest quality Video & Audio
  - Audio Only (MP3 format conversion)
  - Native MP4 / Forced MP4 Option
- Easy folder saving destination selector with memory state (`settings.json`).

## Requirements

Ensure you have Python installed, then install the required dependencies:

```bash
pip install -r requirements.txt
```

_Note: For MP3 and MP4 conversion, `ffmpeg` is required. When running from source it must be on your PATH. In the packaged `.exe`, `ffmpeg.exe`/`ffprobe.exe` are bundled inside the app (see `ffmpeg/README.txt`), so end users do **not** need to install anything._

## Building the .exe (developers)

1. Place `ffmpeg.exe` and `ffprobe.exe` into the `ffmpeg/` folder (see `ffmpeg/README.txt`).
2. Build with PyInstaller:

```bash
pyinstaller VideoDownloaderPro.spec
```

The output in `dist/VideoDownloaderPro/` is fully self-contained — no Python, no IDE, and no separate ffmpeg install required on the end user's machine.

## How to run

Run the main entry file:

```bash
python VideoDownloaderPro.py
```
