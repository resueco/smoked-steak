import os
import re
import shutil
from pathlib import Path
from typing import Literal

import anyio
import asyncclick as click
import msgspec

from steak.common.constants import IMAGE_EXTENSIONS, LOSSY_EXTENSIONS
from steak.common.files import process_files
from steak.converter.naming import QUALITY_TAG_RE, format_quality_tag
from steak.errors import InvalidSampleRate
from steak.tagger.audio_info import gather_audio_info

BitDepth = Literal[16, 24]

SOX_DEPTH_ARGS: dict[BitDepth, list[str]] = {
    16: ["-R", "-G", "-b", "16"],
    24: ["-R", "-G"],
}

FLAC_FOLDER_RE = re.compile(r"(?:(?:16|24)\s*bit\s+)?FLAC", flags=re.IGNORECASE)
LOSSLESS_FOLDER_RE = re.compile(r"Lossless", flags=re.IGNORECASE)


class ConvertItem(msgspec.Struct, frozen=True):
    """A file that needs sample rate / bit depth conversion."""

    src: str
    dst: str
    sample_rate: int
    target_rate: int


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------


def _resolve_sample_rate(sample_rate: int) -> int:
    """Determine the standard sample rate family for a given rate.

    Args:
        sample_rate: The original sample rate.

    Returns:
        44100 or 48000 depending on the rate family.

    Raises:
        InvalidSampleRate: If the rate doesn't belong to either family.
    """
    if sample_rate % 44100 == 0:
        return 44100
    if sample_rate % 48000 == 0:
        return 48000
    raise InvalidSampleRate


def _build_output_path(path: str, bit_depth: BitDepth, sample_rate: int | None) -> str:
    """Generate the output directory path based on source path and conversion params.

    Args:
        path: Source album directory path.
        bit_depth: Target bit depth.
        sample_rate: Target sample rate, or None.

    Returns:
        The output directory path string.
    """
    foldername = os.path.basename(path)

    # Bit depth and sample rate belong in the separate quality tag. Normalize
    # legacy labels such as "24bit FLAC" while keeping combined tags such as
    # "[WEB FLAC]" intact.
    if FLAC_FOLDER_RE.search(foldername):
        foldername = FLAC_FOLDER_RE.sub("FLAC", foldername)
    elif LOSSLESS_FOLDER_RE.search(foldername):
        foldername = LOSSLESS_FOLDER_RE.sub("FLAC", foldername)
    else:
        foldername += " [FLAC]"

    if sample_rate is not None:
        quality_tag = format_quality_tag(bit_depth, sample_rate)
        if QUALITY_TAG_RE.search(foldername):
            foldername = QUALITY_TAG_RE.sub(quality_tag, foldername)
        else:
            foldername += f" {quality_tag}"
    elif QUALITY_TAG_RE.search(foldername):
        # This fallback is useful to callers of the pure helper. convert_folder
        # normally resolves the real target rate before building the path.
        foldername = QUALITY_TAG_RE.sub(
            lambda match: f"[{bit_depth}B-{match.group('sample_rate')}kHz]",
            foldername,
        )

    return os.path.join(os.path.dirname(path), foldername)


def _collect_convert_items(
    path: str,
    new_path: str,
    sample_rate: int | None,
    audio_info: dict[str, dict] | None = None,
) -> list[ConvertItem]:
    """Collect all 24-bit FLAC files and compute their output paths and target rates.

    Args:
        path: Source album directory path.
        new_path: Destination album directory path.
        sample_rate: Explicit target sample rate, or None for automatic.
        audio_info: Previously gathered audio properties, when available.

    Returns:
        List of ConvertItem structs.
    """
    src_path = Path(path)
    dst_path = Path(new_path)
    if audio_info is None:
        audio_info = gather_audio_info(path)

    items: list[ConvertItem] = []
    for info_file, file_info in audio_info.items():
        if file_info["precision"] != 24:
            continue
        src_file = src_path / info_file
        rel = Path(info_file)
        dst_file = dst_path / rel
        target_rate = sample_rate if sample_rate else _resolve_sample_rate(file_info["sample rate"])
        items.append(
            ConvertItem(
                src=str(src_file),
                dst=str(dst_file),
                sample_rate=file_info["sample rate"],
                target_rate=target_rate,
            )
        )

    return items


# ---------------------------------------------------------------------------
# Side-effect functions
# ---------------------------------------------------------------------------


def _validate_lossless(path: str) -> None:
    """Validate that a folder contains no lossy audio files.

    Args:
        path: Path to the directory to validate.

    Raises:
        click.Abort: If a lossy file is found.
    """
    for _root, _, files in os.walk(path):
        for f in files:
            if os.path.splitext(f)[1].lower() in LOSSY_EXTENSIONS:
                click.secho(f"A lossy file was found in the folder ({f}).", fg="red")
                raise click.Abort


def _copy_extra_files(
    path: str,
    new_path: str,
    convert_srcs: frozenset[str],
    *,
    essential_only: bool = False,
) -> None:
    """Copy non-conversion files (images, text, 16-bit audio) to the output directory.

    Args:
        path: Source album directory path.
        new_path: Destination album directory path.
        convert_srcs: Set of source paths that will be converted (to exclude).
        essential_only: If True, only copy image files; skip everything else.
    """
    src_path = Path(path)
    dst_path = Path(new_path)

    for p in src_path.rglob("*"):
        if not p.is_file() or str(p) in convert_srcs:
            continue
        rel = p.relative_to(src_path)
        if essential_only and p.suffix.lower() not in IMAGE_EXTENSIONS:
            click.secho(f"Skip  {rel}", fg="yellow")
            continue
        out = dst_path / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        click.secho(f"Copy  {rel}", fg="cyan")
        shutil.copy(p, out)


async def _convert_audio_files(
    items: list[ConvertItem],
    bit_depth: BitDepth,
) -> None:
    """Convert audio files concurrently using sox.

    Args:
        items: List of ConvertItem structs.
        bit_depth: Target bit depth (16 or 24).
    """
    if not items:
        return

    async def _convert_one(file: str, idx: int) -> None:
        item = items[idx]
        Path(item.dst).parent.mkdir(parents=True, exist_ok=True)

        command = [
            "sox",
            item.src,
            *SOX_DEPTH_ARGS[bit_depth],
            item.dst,
            "rate",
            "-v",
            "-L",
            str(item.target_rate),
            "dither",
        ]

        result = await anyio.run_process(command, check=False)
        if result.returncode != 0:
            err = result.stderr.decode() if result.stderr else ""
            if err:
                click.secho(err, fg="yellow")
            raise RuntimeError(f"sox conversion failed for {os.path.basename(item.src)} with code {result.returncode}")

    file_paths = [item.src for item in items]
    await process_files(file_paths, _convert_one, "Converting")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def convert_folder(
    path: str,
    bit_depth: BitDepth = 16,
    sample_rate: int | None = None,
    essential_only: bool = False,
) -> tuple[int | None, str]:
    """Convert a folder of 24-bit FLAC files to the target bit depth.

    Args:
        path: Path to the source album directory.
        bit_depth: Target bit depth. Defaults to 16.
        sample_rate: Target sample rate. None for automatic detection.
        essential_only: If True, only image files are copied; all other extra
            files (scans, cues, logs, etc.) are skipped.

    Returns:
        Tuple of (final_sample_rate, new_folder_path).
    """
    _validate_lossless(path)
    audio_info = gather_audio_info(path)
    target_rates = {
        sample_rate if sample_rate is not None else _resolve_sample_rate(file_info["sample rate"])
        for file_info in audio_info.values()
        if file_info["precision"] == 24
    }
    folder_sample_rate = sample_rate
    if folder_sample_rate is None and len(target_rates) == 1:
        folder_sample_rate = next(iter(target_rates))

    new_path = _build_output_path(path, bit_depth, folder_sample_rate)

    if os.path.isdir(new_path):
        click.secho(f"{new_path} already exists.", fg="yellow")
        return folder_sample_rate, new_path

    items = _collect_convert_items(path, new_path, sample_rate, audio_info)
    convert_srcs = frozenset(item.src for item in items)
    _copy_extra_files(path, new_path, convert_srcs, essential_only=essential_only)
    await _convert_audio_files(items, bit_depth)

    final_rate = items[-1].target_rate if items else None
    return final_rate or sample_rate, new_path


def generate_conversion_description(url: str, sample_rate: int | None, bit_depth: BitDepth = 16) -> str:
    """Generate a BBCode description for the conversion process.

    Args:
        url: Source URL for attribution.
        sample_rate: The sample rate used in conversion.
        bit_depth: Target bit depth (16 or 24).

    Returns:
        Formatted description string.
    """
    if sample_rate is None:
        return ""
    depth_args = " ".join(SOX_DEPTH_ARGS[bit_depth])
    sox_cmd = f"sox input.flac {depth_args} output.flac rate -v -L {sample_rate} dither"
    return (
        f"Encode Specifics: {bit_depth} bit {sample_rate / 1000:.01f} kHz\n"
        f"[b]Source:[/b] {url}\n"
        f"[b]Transcode process:[/b] [code]{sox_cmd}[/code]"
    )
