import asyncio
from pathlib import Path

import pytest

import steak.converter.downconverting as downconverting
from steak.converter.downconverting import _build_output_path as build_downconversion_path
from steak.converter.transcoding import Bitrate
from steak.converter.transcoding import _build_output_path as build_transcode_path

SOURCE = "/music/Artist — Album (2020) [WEB] [FLAC] [24B-44.1kHz]"


def test_downconversion_replaces_separate_quality_tag() -> None:
    assert build_downconversion_path(SOURCE, 16, 44100) == ("/music/Artist — Album (2020) [WEB] [FLAC] [16B-44.1kHz]")


def test_downconversion_names_lower_sample_rate_and_24_bit_targets() -> None:
    high_resolution_source = "/music/Album [WEB] [FLAC] [24B-192kHz]"

    assert build_downconversion_path(high_resolution_source, 16, 48000) == ("/music/Album [WEB] [FLAC] [16B-48kHz]")
    assert build_downconversion_path(high_resolution_source, 24, 96000) == ("/music/Album [WEB] [FLAC] [24B-96kHz]")


def test_downconversion_normalizes_legacy_flac_label_and_adds_quality() -> None:
    source = "/music/Album [WEB 24bit FLAC]"

    assert build_downconversion_path(source, 16, 44100) == "/music/Album [WEB FLAC] [16B-44.1kHz]"


def test_downconversion_without_explicit_rate_updates_existing_bit_depth() -> None:
    assert build_downconversion_path(SOURCE, 16, None) == "/music/Artist — Album (2020) [WEB] [FLAC] [16B-44.1kHz]"


def test_automatic_downconversion_uses_resolved_target_rate(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "Album [WEB] [FLAC] [24B-96kHz]"
    source.mkdir()
    monkeypatch.setattr(
        downconverting,
        "gather_audio_info",
        lambda _path: {"01.flac": {"precision": 24, "sample rate": 96000}},
    )
    monkeypatch.setattr(downconverting, "_copy_extra_files", lambda *_args, **_kwargs: None)

    async def skip_conversion(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(downconverting, "_convert_audio_files", skip_conversion)

    sample_rate, output_path = asyncio.run(downconverting.convert_folder(str(source)))

    assert sample_rate == 48000
    assert output_path == str(tmp_path / "Album [WEB] [FLAC] [16B-48kHz]")


@pytest.mark.parametrize("quality", ["16B-44.1kHz", "24B-44.1kHz", "24B-48kHz", "24B-96kHz"])
@pytest.mark.parametrize("bitrate", ["320", "V0"])
def test_mp3_transcodes_replace_format_and_remove_lossless_quality(quality: str, bitrate: Bitrate) -> None:
    source = f"/music/Artist — Album (2020) [WEB] [FLAC] [{quality}]"

    assert build_transcode_path(source, bitrate) == f"/music/Artist — Album (2020) [WEB] [MP3 {bitrate}]"


def test_mp3_transcode_normalizes_legacy_lossless_labels() -> None:
    assert build_transcode_path("/music/Album [WEB 24bit FLAC]", "320") == "/music/Album [WEB MP3 320]"
    assert build_transcode_path("/music/Album [WEB Lossless]", "V0") == "/music/Album [WEB MP3 V0]"
