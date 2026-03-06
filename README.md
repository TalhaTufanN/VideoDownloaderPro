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

_Note: For MP3 and MP4 conversion, `ffmpeg` must be installed on your system and accessible via PATH._

## How to run

Run the main entry file:

```bash
python VideoDownloaderPro.py
```
