#!/usr/bin/env python3
"""Download YouTube videos and playlists listed in tasks.csv."""

import csv
import os
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.parse import urlsplit


MIN_HEIGHT = 720
MERGED_FORMAT = f"bestvideo[height>={MIN_HEIGHT}]+bestaudio/best[height>={MIN_HEIGHT}]"
COMBINED_FORMAT = f"best[height>={MIN_HEIGHT}]"
SUPPORTED_BROWSERS = {
    "brave", "chrome", "chromium", "edge", "firefox",
    "opera", "safari", "vivaldi", "whale",
}
TASKS_FILE = Path(__file__).resolve().with_name("tasks.csv")


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


def task_inputs(row: list[str]) -> tuple[str, bool, Path, dict]:
    if len(row) != 5:
        raise ValueError("expected five columns: URL, playlist, directory, cookies, status")

    url, playlist_answer, directory_answer, cookies_answer, _ = (value.strip() for value in row)
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
    except ValueError as error:
        raise ValueError("invalid YouTube URL") from error
    if parts.scheme not in {"http", "https"} or not (
        host in {"youtube.com", "youtu.be", "youtube-nocookie.com"}
        or host.endswith(".youtube.com")
        or host.endswith(".youtube-nocookie.com")
    ):
        raise ValueError("invalid YouTube URL")

    if playlist_answer.lower() not in {"y", "yes", "n", "no"}:
        raise ValueError("playlist must be y or n")
    if not directory_answer:
        raise ValueError("directory is empty")
    directory = Path(directory_answer).expanduser()
    if not directory.is_absolute():
        directory = TASKS_FILE.parent / directory
    directory = directory.resolve()

    cookies = {}
    if cookies_answer:
        if cookies_answer.lower() in SUPPORTED_BROWSERS:
            cookies = {"cookiesfrombrowser": (cookies_answer.lower(),)}
        else:
            cookie_file = Path(cookies_answer).expanduser()
            if not cookie_file.is_absolute():
                cookie_file = TASKS_FILE.parent / cookie_file
            cookie_file = cookie_file.resolve()
            if not cookie_file.is_file():
                raise ValueError("cookies must be a supported browser or an existing cookies.txt file")
            cookies = {"cookiefile": str(cookie_file)}

    return url, playlist_answer.lower() in {"y", "yes"}, directory, cookies


def save_tasks(rows: list[list[str]]) -> None:
    """Replace the CSV after each completed task so progress survives a restart."""
    mode = TASKS_FILE.stat().st_mode
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=TASKS_FILE.parent,
            prefix=".tasks-", suffix=".csv", delete=False,
        ) as temporary:
            temporary_name = temporary.name
            csv.writer(temporary).writerows(rows)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.chmod(temporary_name, mode)
        os.replace(temporary_name, TASKS_FILE)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def download_task(url: str, playlist: bool, directory: Path, cookies: dict,
                  yt_dlp, deno_path: str, ffmpeg: str | None) -> bool:
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
            options["ignoreerrors"] = True
            options["sleep_interval_requests"] = 1
            options["sleep_interval"] = 5
            options["max_sleep_interval"] = 10
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
            print(
                "Some videos failed. Completed videos are saved; rerun with the same "
                "playlist and directory to retry the missing ones. If YouTube keeps "
                "asking you to sign in, use a fresh YouTube cookies.txt file.",
                file=sys.stderr,
            )
            return False
    except (OSError, yt_dlp.utils.YoutubeDLError) as error:
        print(f"Download failed: {error}", file=sys.stderr)
        if "sign in to confirm" in str(error).lower() or "not a bot" in str(error).lower():
            print(
                "YouTube rejected this session. Rerun later with the same directory, "
                "or use a fresh YouTube cookies.txt file in tasks.csv.",
                file=sys.stderr,
            )
        if not ffmpeg:
            print("Install all requirements to enable merging: .venv/bin/python -m pip install -r requirements.txt", file=sys.stderr)
        return False

    print(f"Saved to {directory}")
    return True


def main() -> int:
    try:
        with TASKS_FILE.open(newline="", encoding="utf-8-sig") as file:
            rows = list(csv.reader(file))
    except (OSError, csv.Error) as error:
        print(f"Cannot read {TASKS_FILE}: {error}", file=sys.stderr)
        return 1

    pending = [(number, row) for number, row in enumerate(rows, 1)
               if row and (len(row) != 5 or row[-1].strip().lower() != "done")]
    if not pending:
        print("No pending tasks.")
        return 0

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

    failed = False
    for number, row in pending:
        try:
            inputs = task_inputs(row)
        except ValueError as error:
            print(f"Row {number}: {error}", file=sys.stderr)
            failed = True
            continue
        print(f"Row {number}: downloading {inputs[0]}")
        try:
            if not download_task(*inputs, yt_dlp, deno_path, ffmpeg):
                failed = True
                continue
            row[-1] = "done"
            save_tasks(rows)
            print(f"Row {number}: done")
        except OSError as error:
            print(f"Row {number}: could not update tasks.csv: {error}", file=sys.stderr)
            return 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
