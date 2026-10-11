#!/usr/bin/env python3
"""Interactively download a YouTube video or playlist at 720p or higher."""

from pathlib import Path
import shutil
import sys
from urllib.parse import urlsplit


MIN_HEIGHT = 720
MERGED_FORMAT = f"bestvideo[height>={MIN_HEIGHT}]+bestaudio/best[height>={MIN_HEIGHT}]"
COMBINED_FORMAT = f"best[height>={MIN_HEIGHT}]"


def find_ffmpeg() -> str | None:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, OSError, RuntimeError):
        return None


def ask_url() -> str:
    while True:
        url = input("YouTube URL: ").strip()
        try:
            parts = urlsplit(url)
            host = (parts.hostname or "").lower()
        except ValueError:
            print("Enter a full YouTube URL beginning with https:// or http://.")
            continue

        if parts.scheme in {"http", "https"} and (
            host in {"youtube.com", "youtu.be", "youtube-nocookie.com"}
            or host.endswith(".youtube.com")
            or host.endswith(".youtube-nocookie.com")
        ):
            return url
        print("Enter a full YouTube URL beginning with https:// or http://.")


def ask_playlist() -> bool:
    while True:
        answer = input("Download the whole playlist? [y/n]: ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please enter y or n.")


def ask_directory() -> Path:
    while True:
        answer = input("Directory to save files: ").strip()
        if answer:
            return Path(answer).expanduser().resolve()
        print("Please enter a directory.")


def main() -> int:
    try:
        url = ask_url()
        playlist = ask_playlist()
        directory = ask_directory()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return 130

    try:
        import yt_dlp
    except ImportError:
        print("yt-dlp is missing. Install it with: .venv/bin/python -m pip install -r requirements.txt", file=sys.stderr)
        return 1

    ffmpeg = find_ffmpeg()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        if not ffmpeg:
            print("ffmpeg was not found. Trying a 720p+ format that already has audio.")
        template = (
            "%(playlist_index)s - %(title).180B [%(id)s].%(ext)s"
            if playlist else "%(title).180B [%(id)s].%(ext)s"
        )
        options = {
            "format": MERGED_FORMAT if ffmpeg else COMBINED_FORMAT,
            "noplaylist": not playlist,
            "outtmpl": str(directory / template),
            "continuedl": True,
        }
        if playlist:
            options["download_archive"] = str(directory / ".yt-dlp-download-archive.txt")
        if ffmpeg:
            options["merge_output_format"] = "mkv"
            options["ffmpeg_location"] = ffmpeg
        with yt_dlp.YoutubeDL(options) as downloader:
            result = downloader.download([url])
        if result:
            print("Download did not complete successfully.", file=sys.stderr)
            return 1
    except (OSError, yt_dlp.utils.DownloadError) as error:
        print(f"Download failed: {error}", file=sys.stderr)
        if not ffmpeg:
            print("Install all requirements to enable merging: .venv/bin/python -m pip install -r requirements.txt", file=sys.stderr)
        return 1

    print(f"Saved to {directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
