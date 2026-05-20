import asyncio
from copy import deepcopy

from steak import cfg
from steak.sources.qobuz import QobuzBase
from steak.tagger import metadata as metadata_mod
from steak.tagger import metadata_validator_base


def make_release_data() -> dict:
    return {
        "artists": [("Example Artist", "main")],
        "title": "Example Release",
        "group_year": "2026",
        "year": "2026",
        "date": None,
        "edition_title": None,
        "label": None,
        "catno": None,
        "rls_type": None,
        "genres": ["Electronic"],
        "format": "FLAC",
        "encoding": "Lossless",
        "encoding_vbr": False,
        "scene": False,
        "source": "WEB",
        "cover": None,
        "upc": None,
        "comment": None,
        "urls": [],
        "tracks": {
            "1": {
                "1": {
                    "track#": "1",
                    "disc#": "1",
                    "tracktotal": "1",
                    "disctotal": "1",
                    "artists": [("Example Artist", "main")],
                    "title": "Track One",
                    "replay_gain": None,
                    "peak": None,
                    "isrc": None,
                    "explicit": None,
                    "format": None,
                    "streamable": None,
                }
            }
        },
    }


class DummyBandcampScraper:
    regex = type("Regex", (), {"match": staticmethod(lambda value: "/album/" in value)})

    async def scrape_release(self, url: str):
        data = deepcopy(make_release_data())
        data["title"] = "Bandcamp Title"
        data["urls"] = [url]
        return data


class DummyBandcampSource:
    Scraper = DummyBandcampScraper


class DummyQobuzScraper:
    regex = QobuzBase.regex

    async def scrape_release(self, url: str):
        data = deepcopy(make_release_data())
        data["title"] = "Qobuz Title"
        data["urls"] = [url]
        return data


class DummyQobuzSource:
    Scraper = DummyQobuzScraper


def test_qobuz_regex_matches_open_qobuz_urls() -> None:
    assert QobuzBase.regex.match("https://open.qobuz.com/album/0887396827479")


def test_select_choice_routes_open_qobuz_urls_to_qobuz_before_bandcamp(monkeypatch) -> None:
    async def prompt_url(*args, **kwargs):
        return "*https://open.qobuz.com/album/0887396827479"

    monkeypatch.setattr(metadata_mod.click, "prompt", prompt_url)
    monkeypatch.setattr(
        metadata_mod,
        "METASOURCES",
        {
            "Qobuz": DummyQobuzSource,
            "Bandcamp": DummyBandcampSource,
        },
    )

    metadata, source_url = asyncio.run(metadata_mod._select_choice({}, make_release_data()))

    assert source_url == "https://open.qobuz.com/album/0887396827479"
    assert metadata["title"] == "Qobuz Title"


def test_select_choice_disabled_source_does_not_fall_through_to_bandcamp(monkeypatch) -> None:
    original_disabled_sources = list(cfg.metadata.disabled_sources)

    async def prompt_url(*args, **kwargs):
        return "*https://open.qobuz.com/album/0887396827479"

    try:
        cfg.metadata.disabled_sources = ["Qobuz"]
        monkeypatch.setattr(metadata_mod.click, "prompt", prompt_url)
        monkeypatch.setattr(
            metadata_mod,
            "METASOURCES",
            {
                "Qobuz": DummyQobuzSource,
                "Bandcamp": DummyBandcampSource,
            },
        )

        metadata, source_url = asyncio.run(metadata_mod._select_choice({}, make_release_data()))
    finally:
        cfg.metadata.disabled_sources = original_disabled_sources

    assert source_url == "https://open.qobuz.com/album/0887396827479"
    assert metadata["title"] == "Example Release"


def test_get_metadata_prints_metadata_services(monkeypatch, capsys) -> None:
    original_disabled_sources = list(cfg.metadata.disabled_sources)

    async def fake_run_metasearch(*args, **kwargs):
        return {}

    async def fake_select_choice(_choices, _rls_data):
        return deepcopy(make_release_data()), None

    try:
        cfg.metadata.disabled_sources = ["MusicBrainz", "Beatport"]
        monkeypatch.setattr(metadata_mod, "run_metasearch", fake_run_metasearch)
        monkeypatch.setattr(metadata_mod, "_print_search_results", lambda _results, _rls_data: {})
        monkeypatch.setattr(metadata_mod, "_select_choice", fake_select_choice)

        asyncio.run(metadata_mod.get_metadata("/tmp", {"01.flac": {}}, make_release_data()))
    finally:
        cfg.metadata.disabled_sources = original_disabled_sources

    output = capsys.readouterr().out
    assert "Search services:" in output
    assert "Bandcamp" in output
    assert "MusicBrainz" not in output
    assert "Beatport" not in output
    assert "Metadata URL services:" in output
    assert "Qobuz" in output
    assert "Tidal" in output


def test_clean_metadata_normalizes_non_main_artist_roles_to_guest() -> None:
    metadata = make_release_data()
    metadata["artists"] = [
        ("Example Artist", "main"),
        ("Guest Artist", "guest"),
        ("Composer Person", "composer"),
        ("Remixer Person", "remixer"),
        ("Conductor Person", "conductor"),
        ("Compiler Person", "djcompiler"),
        ("Producer Person", "producer"),
    ]
    metadata["tracks"]["1"]["1"]["artists"] = [
        ("Example Artist", "main"),
        ("Guest Artist", "guest"),
        ("Composer Person", "composer"),
        ("Remixer Person", "remixer"),
        ("Conductor Person", "conductor"),
        ("Compiler Person", "djcompiler"),
        ("Producer Person", "producer"),
    ]

    cleaned = metadata_mod.clean_metadata(metadata)

    assert cleaned["artists"] == [
        ("Example Artist", "main"),
        ("Guest Artist", "guest"),
        ("Composer Person", "guest"),
        ("Remixer Person", "guest"),
        ("Conductor Person", "guest"),
        ("Compiler Person", "guest"),
        ("Producer Person", "guest"),
    ]
    assert cleaned["tracks"]["1"]["1"]["artists"] == cleaned["artists"]


def test_clean_metadata_prefers_main_when_artist_has_multiple_roles() -> None:
    metadata = make_release_data()
    metadata["tracks"]["1"]["1"]["artists"] = [
        ("Example Artist", "composer"),
        ("Example Artist", "main"),
    ]

    cleaned = metadata_mod.clean_metadata(metadata)

    assert cleaned["artists"] == [("Example Artist", "main")]
    assert cleaned["tracks"]["1"]["1"]["artists"] == [("Example Artist", "main")]


def test_clean_metadata_promotes_first_guest_when_track_has_no_main_artist() -> None:
    metadata = make_release_data()
    metadata["tracks"]["1"]["1"]["artists"] = [
        ("Composer Person", "composer"),
        ("Remixer Person", "remixer"),
    ]

    cleaned = metadata_mod.clean_metadata(metadata)

    assert cleaned["artists"] == [("Composer Person", "main"), ("Remixer Person", "guest")]
    assert cleaned["tracks"]["1"]["1"]["artists"] == [("Composer Person", "main"), ("Remixer Person", "guest")]


def test_clean_metadata_fills_missing_year_from_group_year() -> None:
    metadata = make_release_data()
    metadata["group_year"] = "2026"
    metadata["year"] = None

    cleaned = metadata_mod.clean_metadata(metadata)

    assert cleaned["group_year"] == "2026"
    assert cleaned["year"] == "2026"


def test_clean_metadata_fills_missing_group_year_from_year() -> None:
    metadata = make_release_data()
    metadata["group_year"] = None
    metadata["year"] = "2026"

    cleaned = metadata_mod.clean_metadata(metadata)

    assert cleaned["group_year"] == "2026"
    assert cleaned["year"] == "2026"


def test_clean_metadata_normalizes_dk_label_to_self_released() -> None:
    metadata = make_release_data()
    metadata["label"] = "Records DK"

    cleaned = metadata_mod.clean_metadata(metadata)

    assert cleaned["label"] == "Self-Released"


def test_metadata_validator_normalizes_dk_label_to_self_released() -> None:
    metadata = make_release_data()
    metadata["label"] = "Records DK"
    metadata["rls_type"] = "Album"

    validated = metadata_validator_base(metadata)

    assert validated["label"] == "Self-Released"
