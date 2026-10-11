# YouTube downloader

This interactive Python script downloads one YouTube video or an entire playlist.
It selects the best available video at **720p or higher** (interpreting the
requested 700 or higher quality as a minimum of 720p) and includes audio in
each finished file. `yt-dlp` uses `ffmpeg` to merge separate video and audio
streams when YouTube does not provide them together. Temporary streams are
removed after merging.

## Setup

Install Python 3, then create a virtual environment and install the dependencies.
`imageio-ffmpeg` supplies an `ffmpeg` executable inside the virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The script also accepts a system `ffmpeg` on `PATH`. If neither is available,
it can only download formats that already contain both video and audio.

## Run

```sh
.venv/bin/python download_youtube.py
```

Enter the YouTube URL, answer `y` for a whole playlist or `n` for one video,
then enter the save directory. A video with no available 720p or higher format
will fail instead of being saved at a lower resolution. Without `ffmpeg`, a
720p or higher format must already contain audio. Merged files use MKV;
videos that YouTube already supplies with audio may retain their original
container (such as MP4).

For playlists, rerun the script with the same URL and save directory to resume.
The hidden `.yt-dlp-download-archive.txt` file in that directory records videos
that finished successfully, so they are skipped on later runs. Incomplete
`.part` files are resumed when possible. Keep the archive file and partial
files in place between runs.
