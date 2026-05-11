from typing import Any

import asyncclick as click

from steak import cfg
from steak.errors import ScrapeError
from steak.tagger.sources import (
    apple_music,
    bandcamp,
    beatport,
    deezer,
    discogs,
    musicbrainz,
    qobuz,
    tidal,
)

METASOURCES = {
    "MusicBrainz": musicbrainz,
    "Apple Music": apple_music,
    "Deezer": deezer,
    "Discogs": discogs,
    "Beatport": beatport,
    "Qobuz": qobuz,
    "Tidal": tidal,
    "Bandcamp": bandcamp,  # Must be last due to the catch-all nature of its URLs.
}


def get_metadata_sources(sources: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return direct metadata URL scrapers after applying config-level disables."""
    selected_sources = (
        METASOURCES
        if sources is None
        else {name: source for name, source in METASOURCES.items() if name in sources}
    )
    disabled_sources = {source.casefold() for source in cfg.metadata.disabled_sources}
    return {name: source for name, source in selected_sources.items() if name.casefold() not in disabled_sources}


def is_metadata_source_disabled(source_name: str) -> bool:
    return source_name.casefold() in {source.casefold() for source in cfg.metadata.disabled_sources}


async def run_metadata(
    url: str,
    sources: dict[str, Any] | None = None,
    return_source_name: bool = False,
) -> dict[str, Any] | tuple[dict[str, Any], str]:
    """Run a scrape for the metadata of a URL.

    Args:
        url: The URL to scrape metadata from.
        sources: Optional dict of sources to use, defaults to all.
        return_source_name: If True, return tuple of (metadata, source_name).

    Returns:
        Metadata dict, or tuple of (metadata, source_name) if return_source_name is True.

    Raises:
        ScrapeError: If URL doesn't match any scraper.
    """
    selected_sources = (
        METASOURCES
        if sources is None
        else {name: source for name, source in METASOURCES.items() if name in sources}
    )
    for name, source in selected_sources.items():
        if source.Scraper.regex.match(url):
            if is_metadata_source_disabled(name):
                raise ScrapeError(f"{name} metadata source is disabled.")
            click.secho(f"Getting metadata from {name}.", fg="cyan")
            if return_source_name:
                return await source.Scraper().scrape_release(url), name
            return await source.Scraper().scrape_release(url)
    raise ScrapeError("URL did not match a scraper.")
