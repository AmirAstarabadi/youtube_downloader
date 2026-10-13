# YouTube downloader

This Python script downloads YouTube videos and playlists from `tasks.csv` in
the project directory.
It selects the best available video at **720p or higher** (interpreting the
requested 700 or higher quality as a minimum of 720p) and includes audio in
each finished file. `yt-dlp` uses `ffmpeg` to merge separate video and audio
streams when YouTube does not provide them together. Temporary streams are
removed after merging.

## Setup

Install Python 3, then create a virtual environment and install the dependencies.
`imageio-ffmpeg` supplies `ffmpeg`. The `yt-dlp[default,deno]` package installs
YouTube's JavaScript challenge scripts and a Deno runtime in the virtual
environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

On Linux, the requirements also include `secretstorage` for Chromium browser
cookies stored in the desktop keyring.

The script also accepts a system `ffmpeg` on `PATH`. If neither is available,
it can only download formats that already contain both video and audio.

## Run

```sh
.venv/bin/python download_youtube.py
```

Each CSV row has five fields, without a header: `URL,playlist,directory,cookies,status`.
Use `y` to download a whole playlist or `n` for one video. The cookies field
can be empty for public videos, a browser name such as `firefox` or `chrome`,
or a path to a Netscape-format `cookies.txt` file. Relative directory and
cookie paths are resolved from the project directory. Sign in to YouTube in
the browser first if YouTube asks you to confirm you are not a bot. Keep
exported cookie files private and outside the project when possible. For
signed-in sessions, the script also enables YouTube's web embedded client to
work around the current "page needs to be reloaded" response.

Set the last field to `pending` for a new task. The script processes rows in
order and changes a row to `done` immediately after its download succeeds.
It skips `done` rows on later runs. Failed rows keep their previous status so
they can be retried; other rows still run. A run exits with an error if any row
fails.

A video with no available 720p or higher format
will fail instead of being saved at a lower resolution. Without `ffmpeg`, a
720p or higher format must already contain audio. Merged files use MKV;
videos that YouTube already supplies with audio may retain their original
container (such as MP4).

For playlists, rerun the script with the same URL and save directory to resume.
The hidden `.yt-dlp-download-archive.txt` file in that directory records videos
that finished successfully, so they are skipped on later runs. Incomplete
`.part` files are resumed when possible. Keep the archive file and partial
files in place between runs. The script waits between playlist requests and
videos. If one item fails, it tries later items and exits with an error; rerun
the same playlist to retry any missing videos.

If Chrome cookies work at first but YouTube later asks you to sign in again,
the browser session may have changed. For a longer-running playlist, use a
fresh YouTube-only `cookies.txt` file from a private browser window, following
the [yt-dlp YouTube cookie export guide](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies).
Enter that file's path at the Cookies prompt. Keep the file private.
