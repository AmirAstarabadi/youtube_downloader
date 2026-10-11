#!/usr/bin/env python3
"""Interactively download a YouTube video or playlist at 720p or higher."""

from pathlib import Path
import shutil
import sys
from urllib.parse import urlsplit


MIN_HEIGHT = 720
MERGED_FORMAT = f"bestvideo[height>={MIN_HEIGHT}]+bestaudio/best[height>={MIN_HEIGHT}]"
COMBINED_FORMAT = f"best[height>={MIN_HEIGHT}]"
SUPPORTED_BROWSERS = {
    "brave", "chrome", "chromium", "edge", "firefox",
    "opera", "safari", "vivaldi", "whale",
}


def find_ffmpeg() -> str | None:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, OSError, RuntimeError):
        return None


def find_deno() -> str | None:
    try:
        import deno

        return str(deno.find_deno_bin())
    except (ImportError, OSError, RuntimeError):
        return shutil.which("deno")


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


def ask_cookies() -> dict:
    while True:
        answer = input(
            "Cookies (Enter for none, browser name, or cookies.txt path): "
        ).strip()
        if not answer:
            return {}
        if answer.lower() in SUPPORTED_BROWSERS:
            return {"cookiesfrombrowser": (answer.lower(),)}

        cookie_file = Path(answer).expanduser().resolve()
        if cookie_file.is_file():
            return {"cookiefile": str(cookie_file)}
        print("Enter a supported browser name or an existing cookies.txt file path.")


def main() -> int:
    try:
        url = ask_url()
        playlist = ask_playlist()
        directory = ask_directory()
        cookies = ask_cookies()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return 130

    try:
        import yt_dlp
        import yt_dlp_ejs  # noqa: F401 - required for YouTube JS challenges
    except ImportError:
        print("YouTube downloader dependencies are missing. Install them with: .venv/bin/python -m pip install -r requirements.txt", file=sys.stderr)
        return 1

    deno_path = find_deno()
    if not deno_path:
        print("Deno is required for YouTube's JavaScript challenges. Install it with: .venv/bin/python -m pip install -r requirements.txt", file=sys.stderr)
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
            "js_runtimes": {"deno": {"path": deno_path}},
            **cookies,
        }
        if playlist:
            options["download_archive"] = str(directory / ".yt-dlp-download-archive.txt")
        if cookies:
            options["extractor_args"] = {
                "youtube": {"player_client": ["default", "web_embedded"]}
            }
        if ffmpeg:
            options["merge_output_format"] = "mkv"
            options["ffmpeg_location"] = ffmpeg
        with yt_dlp.YoutubeDL(options) as downloader:
            result = downloader.download([url])
        if result:
            print("Download did not complete successfully.", file=sys.stderr)
            return 1
    except (OSError, yt_dlp.utils.YoutubeDLError) as error:
        print(f"Download failed: {error}", file=sys.stderr)
        if "sign in to confirm" in str(error).lower() or "not a bot" in str(error).lower():
            print(
                "Sign in to YouTube in your browser, then rerun and enter that browser "
                "at the Cookies prompt (or provide a Netscape cookies.txt file).",
                file=sys.stderr,
            )
        if not ffmpeg:
            print("Install all requirements to enable merging: .venv/bin/python -m pip install -r requirements.txt", file=sys.stderr)
        return 1

    print(f"Saved to {directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
