# smoked-steak

Smoked Steak is an interactive command-line tool for checking, describing, and uploading music releases to
Gazelle-based trackers. It supports RED, OPS, and DIC and can continue seeding an upload locally or on remote
seedboxes.

Smoked Steak is based on [Smoked Salmon](https://github.com/smokin-salmon/smoked-salmon). Full credit goes to the
Smoked Salmon project and its contributors for the original tool; this project contains modifications made on top
of that work.

The upload workflow reads tags from the source files and combines them with online metadata for the tracker
submission. It does **not** retag audio files or rename release folders as part of metadata review.

## 🌟 Features

- **Interactive, multi-tracker uploads** – Upload a release to RED, OPS, and DIC in one session.
- **Metadata retrieval and review** – Combine metadata from Apple Music, Bandcamp, Beatport, Deezer, Discogs,
  MusicBrainz, Qobuz, and Tidal, then review it before submission.
- **Optional AI metadata review** – Research and verify album-level metadata through an OpenAI-compatible API.
- **Audio and folder checks** – Validate FLAC/MP3 integrity, CD ripping logs and checksums, folder structure, MQA
  markers, and possible 24-bit upconverts.
- **Duplicate and request checks** – Find existing tracker groups, avoid duplicate editions, and identify requests
  that the upload can fill.
- **Descriptions and covers** – Generate BBCode tracklists, source links, encoding details, and upload cover art via
  PTPIMG, PTScreens, OEImg, ImgBB, Catbox, ImgBox, Ra, or RED's internal image host.
- **Multi-format uploads** – Downconvert high-resolution FLAC and create MP3 320/V0 editions, then upload the
  selected formats to the same release group.
- **Torrent creation and seeding** – Generate private torrents, copy or transfer releases with local paths or
  rclone, and inject torrents into qBittorrent, Transmission, Deluge, or ruTorrent.
- **Standalone utilities** – Search or inspect metadata, upload images, generate descriptions, recompress FLAC,
  transcode audio, and run individual file checks.
- **Update notifications** – Optionally report when a newer release is available.

## 📥 Installation

Manual installation instructions can be found on the
[Wiki](https://github.com/resueco/smoked-steak/wiki/Installation).

### 🔹 Install smoked-steak

These steps use [`uv`](https://github.com/astral-sh/uv) to install the package. [`pipx`](https://github.com/pypa/pipx)
also works. Both isolate Smoked Steak from the system Python installation.

#### Linux
1. Install system packages:
    ```bash
    sudo apt install git sox flac mp3val curl lame
    ```

2. Install uv:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

3. Install smoked-steak package from github:
	```bash
	uv tool install git+https://github.com/resueco/smoked-steak
	```

#### Windows
1. Install required system packages using winget:
    ```powershell
    winget install -e Git.Git
    winget install -e ChrisBagwell.SoX Xiph.FLAC LAME.LAME ring0.MP3val.WF
    ```

2. Fix sox Unicode filename handling issue on Windows:
    ```powershell
    $soxDir = $((Get-Command sox).Source | Split-Path)
    $zipPath = Join-Path -Path $soxDir -ChildPath "sox_windows_fix.zip"
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/DevYukine/red_oxide/master/.github/dependency-fixes/sox_windows_fix.zip" -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $soxDir -Force
    regedit "$soxDir\PreferExternalManifest.reg"
    Remove-Item $zipPath
    ```

3. Install uv:
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

4. Install smoked-steak package from github:
	```powershell
	uv tool install git+https://github.com/resueco/smoked-steak
	```

#### macOS
1. Install Homebrew (if you haven't already):
    ```bash
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ```

2. Install system packages using Homebrew:
    ```bash
    brew install git sox flac mp3val curl lame
    ```

3. Install uv:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

4. Install smoked-steak package from github:
	```bash
	uv tool install git+https://github.com/resueco/smoked-steak
	```

### 🔹 Initial setup
1. Run smoked-steak for the first time and follow the instructions to create a default configuration:
	```
	steak-user@smoked-steak:~$ smoked-steak
	Could not find configuration path at /home/steak-user/.config/smoked-steak/config.toml.
	Do you want smoked-steak to create a default config file at /home/steak-user/.config/smoked-steak/config.toml? [y/N]:
	```

2. Edit `config.toml` to add tracker sessions, API keys, existing download/torrent directories, and your preferred
   image hosts. See the [configuration template](src/steak/data/config.default.toml) and
   [Configuration Wiki](https://github.com/resueco/smoked-steak/wiki/Configuration).

3. Use the `checkconf` command to verify that the connection to the trackers is working:

	```
	smoked-steak checkconf
	```

4. Use the `health` command to verify that all necessary command line dependencies are installed:
	```
	smoked-steak health
	```

### 🐳 Docker Installation

A Docker image is generated per release.  
**Disclaimer**: I am not actively using the docker image myself, feedback is appreciated regarding that guide.

1. Pull the image:

   ```bash
   # Stable release
   docker pull ghcr.io/resueco/smoked-steak:latest

   # Development image
   docker pull ghcr.io/resueco/smoked-steak:alpha
   ```

   > The examples below use the `latest` tag. Replace with `alpha` to use the latest development version.

2. Copy the [default configuration](https://github.com/resueco/smoked-steak/blob/main/src/steak/data/config.default.toml)
   to `config.toml` on the host, then add your credentials, directories, and preferences. See the
   [Configuration Wiki](https://github.com/resueco/smoked-steak/wiki/Configuration).

3. Configure rclone if needed. The Docker Compose configuration expects an rclone configuration file. You can get the path to your rclone config file by running `rclone config file` on your host system.

---

### 🔁 Docker Usage

1. **Check Configuration**
   Run the container with the `checkconf` command to verify that the connection to the trackers is working:

   ```bash
   docker run --rm -it --network=host \
   -v /path/to/your/music:/app/.music \
   -v /path/to/your/config.toml/directory:/root/.config/smoked-steak/ \
   -v /path/to/your/generated/dottorrents:/app/.torrents \
   -v /get/this/from/"rclone config file":/root/.config/rclone/rclone.conf  # Optional: only if using rclone features \
   ghcr.io/resueco/smoked-steak:latest checkconf
   ```

2. **Upload**
   Run the upload command directly (replace `checkconf` with any smoked-steak command):

   ```bash
   docker run --rm -it --network=host \
   -v /path/to/your/music:/app/.music \
   -v /path/to/your/config.toml/directory:/root/.config/smoked-steak/ \
   -v /path/to/your/generated/dottorrents:/app/.torrents \
   -v /get/this/from/"rclone config file":/root/.config/rclone/rclone.conf  # Optional: only if using rclone features \
   ghcr.io/resueco/smoked-steak:latest up "/app/.music/path/to/album" -s WEB
   ```

### 💡 Shell Alias (Optional)

To avoid repeating the long `docker run` command, add the following alias to your shell configuration file (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
alias smoked-steak='docker run --rm -it --network=host \
  -v /path/to/your/music:/app/.music \
  -v /path/to/your/config.toml/directory:/root/.config/smoked-steak/ \
  -v /path/to/your/generated/dottorrents:/app/.torrents \
  -v /path/to/your/rclone.conf:/root/.config/rclone/rclone.conf \
  ghcr.io/resueco/smoked-steak:latest'
```

Then use it just like a native install:

```bash
smoked-steak checkconf
smoked-steak health
smoked-steak up "/app/.music/path/to/album" -s WEB
```

---

### ⚠️ Notes

- **Permission issues**
  The image makes `/app` writable, but bind-mounted host directories still use host ownership and permissions.
  If your torrent client cannot read new uploads, you may need to:
  - Manually adjust file/folder ownership (`chown`) or permissions (`chmod`)
  - Ensure the container and torrent client users are compatible
  - Optionally run containers with matching `--user` flags or add `umask` logic
     ```bash
    user: "1001:100"
    environment:
      - PUID=1001
      - PGID=100
     ```

- **`.torrent` directory mapping**
  Depending on `directory.dottorrents_dir` in `config.toml`, you may need an additional volume for torrent output:

  ```bash
  -v /your/host/torrent/output:/app/.torrents
  ```

- **rclone configuration**
  If you're using rclone features, make sure to map your rclone configuration file. This is optional and only needed if you plan to use rclone functionality. You can find your rclone config file location by running `rclone config file` on your host system:

  ```bash
  -v /path/to/your/rclone.conf:/root/.config/rclone/rclone.conf
  ```

---

### 📦 Docker Compose

If using Docker Compose, create a `docker-compose.yml` to define your volume mappings and network settings, then use `docker compose run` to execute any smoked-steak command on demand:

```yaml
services:
  smoked-steak:
    image: ghcr.io/resueco/smoked-steak:latest
    network_mode: host
    volumes:
      - /path/to/your/music:/app/.music
      - /path/to/your/config.toml/directory:/root/.config/smoked-steak/
      - /path/to/your/generated/dottorrents:/app/.torrents
      - /get/this/from/"rclone config file":/root/.config/rclone/rclone.conf  # Optional: only if using rclone features

```

```bash
# Check configuration
docker compose run --rm smoked-steak checkconf

# Upload
docker compose run --rm smoked-steak up "/app/.music/path/to/album" -s WEB
```

## 🚀 Usage

Show the command list with:

```bash
smoked-steak --help
```

Both `smoked-steak` and `steak` invoke the same CLI. Add `--help` to a command or command group for its complete
set of options, for example `smoked-steak up --help` or `smoked-steak check --help`.

### Uploading a release

Start an interactive WEB upload with:

```bash
smoked-steak up "/data/path/to/album" --source WEB
```

Select a tracker and provide the original store page when known:

```bash
smoked-steak up "/data/path/to/album" --source WEB --tracker RED \
  --source-url "https://open.qobuz.com/album/example"
```

During an upload, Smoked Steak:

1. Reads the local tags and audio properties.
2. Checks MQA, possible upconverts, CD logs, folder structure, and audio integrity when applicable.
3. Searches the tracker for an existing group or duplicate edition.
4. Searches metadata providers, combines the results, and opens an interactive metadata review.
5. Optionally runs AI-assisted album-level metadata research when configured.
6. Uploads a cover for new groups, checks matching requests, creates a private torrent, and submits it.
7. Offers eligible FLAC/MP3 conversions, additional trackers, and configured seeding destinations.

Metadata edits made in the review affect the tracker submission only: the upload path does not retag audio or
rename the release folder. Some explicitly selected validation and processing actions **do** modify files. These
include FLAC recompression, integrity sanitization, cover processing, deletion of disallowed files, and truncation
of overlong paths. Downconversion and transcoding create separate output directories. Work from a recoverable copy
when you do not want the source release changed. The legacy `--auto-rename` option remains accepted for CLI
compatibility but currently has no effect.

### Conversion output folder names

Downconversion and transcoding update common release quality tags in the new output folder name. The artist,
album, year, and source portions are preserved. FLAC outputs retain a separate `[FLAC]` format tag and replace the
bit-depth/sample-rate tag with the actual conversion target. MP3 outputs replace the FLAC format tag and remove the
lossless quality tag.

| Conversion | Source tags | Output tags |
| --- | --- | --- |
| 24-bit FLAC to 16-bit/44.1kHz | `[FLAC] [24B-44.1kHz]` | `[FLAC] [16B-44.1kHz]` |
| 24-bit FLAC at 96kHz to automatic 16-bit | `[FLAC] [24B-96kHz]` | `[FLAC] [16B-48kHz]` |
| High-resolution FLAC to 24-bit/96kHz | `[FLAC] [24B-192kHz]` | `[FLAC] [24B-96kHz]` |
| FLAC to MP3 320 | `[FLAC] [16B-44.1kHz]` | `[MP3 320]` |
| FLAC to MP3 V0 | `[FLAC] [24B-48kHz]` | `[MP3 V0]` |

For example:

```text
Artist — Album (2020) [WEB] [FLAC] [24B-44.1kHz]
Artist — Album (2020) [WEB] [FLAC] [16B-44.1kHz]
```

### Common commands

| Command | Purpose |
| --- | --- |
| `smoked-steak checkconf` | Test tracker, metadata-provider, and seedbox configuration. |
| `smoked-steak health` | Show the config path and check required/optional command-line dependencies. |
| `smoked-steak meta URL` | Scrape and print metadata from one supported release URL. |
| `smoked-steak metas QUERY` | Search enabled metadata providers for a release. |
| `smoked-steak descgen URL...` | Combine source URLs into a BBCode tracklist and description. |
| `smoked-steak check log PATH` | Score and validate one ripping log or all logs in a directory. |
| `smoked-steak check integrity PATH` | Validate FLAC/MP3 files and optionally sanitize failures. |
| `smoked-steak check upconv PATH` | Inspect 24-bit FLAC files for possible upconversion. |
| `smoked-steak check mqa PATH` | Check files for an MQA marker. |
| `smoked-steak downconv PATH` | Create a lower-resolution FLAC edition from 24-bit FLAC. |
| `smoked-steak transcode PATH --bitrate 320` | Create an MP3 320 or V0 edition from FLAC. |
| `smoked-steak compress PATH` | Recompress FLAC files to the configured compression level. |
| `smoked-steak images up FILE... --image-host RED` | Upload images to a configured image host. |

Image hosts are selected independently for general uploads and album covers:

```toml
[image]
image_uploader = "RED"
cover_uploader = "RED"
red_key = "your-red-api-key"
```

Supported values are `ptpimg`, `ptscreens`, `oeimg`, `imgbb`, `catbox`, `imgbox`, `ra`, and `RED`.

### Terminal colors

- Default – General information
- Red – Errors or critical failures
- Green – Success messages
- Yellow – Information headers
- Cyan – Section headers
- Magenta – User prompts

More examples are available on the [Wiki Usage page](https://github.com/resueco/smoked-steak/wiki#usage).

### Configuration and dependency checks

```bash
smoked-steak checkconf
smoked-steak checkconf --metadata
smoked-steak checkconf --seedbox
smoked-steak health
```

## 🔄 Updating

For **normal installs**:
```bash
uv tool update smoked-steak
```

For **manual installs**:
```bash
cd smoked-steak
git pull
uv sync
```

For **Docker users**:
```bash
docker pull ghcr.io/resueco/smoked-steak:latest
```
