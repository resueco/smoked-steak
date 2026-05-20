from itertools import chain
from pprint import pprint

import asyncclick as click

from steak.common import commandgroup
from steak.constants import (
    ARTIST_IMPORTANCES,
    RELEASE_TYPES,
    SOURCES,
    TAG_ENCODINGS,
)
from steak.errors import InvalidMetadataError, ScrapeError
from steak.tagger.metadata import normalize_dk_label
from steak.tagger.sources import run_metadata


def validate_source(ctx, param, value):
    try:
        return SOURCES[value.lower()]
    except KeyError:
        raise click.BadParameter(f"{value} is not a valid source.") from None
    except AttributeError:
        raise click.BadParameter(
            "You must provide a source. Possible sources are: " + ", ".join(SOURCES.values())
        ) from None


def validate_encoding(ctx, param, value):
    """Validate and convert encoding parameter.

    Args:
        ctx: Click context.
        param: Click parameter.
        value: The encoding value to validate.

    Returns:
        The validated encoding string or None if not provided.

    Raises:
        click.BadParameter: If the encoding is invalid.
    """
    if value is None:
        return None
    try:
        return TAG_ENCODINGS[value.upper()]
    except KeyError:
        raise click.BadParameter(f"{value} is not a valid encoding.") from None


@commandgroup.command()
@click.argument("url")
async def meta(url: str) -> None:
    """Scrape metadata from release link.

    Args:
        url: URL to scrape metadata from.
    """
    try:
        metadata = await run_metadata(url)
        for key in ["encoding", "media", "encoding_vbr", "source"]:
            if key in metadata and isinstance(metadata, dict):
                del metadata[key]
        click.echo()
        pprint(metadata)
    except ScrapeError as e:
        click.secho(f"Scrape failed: {e}", fg="red")


def metadata_validator_base(metadata):
    """Validate that the provided metadata is not an issue."""
    metadata = normalize_dk_label(metadata)
    artist_importances = set(i for _, i in metadata["artists"])
    if "main" not in artist_importances:
        raise InvalidMetadataError("You must have at least one main artist.")
    for track in chain.from_iterable([d.values() for d in metadata["tracks"].values()]):
        if "main" not in set(i for _, i in track["artists"]):
            raise InvalidMetadataError("You must have at least one main artist per track.")
    if not all(i in ARTIST_IMPORTANCES for i in artist_importances):
        raise InvalidMetadataError(
            "Invalid artist importance detected: {}.".format(
                ", ".join(i for i in artist_importances.difference(ARTIST_IMPORTANCES.values()))
            )
        )
    try:
        metadata["year"] = int(metadata["year"])
    except (ValueError, TypeError):
        raise InvalidMetadataError("Year is not an integer.") from None
    if metadata["rls_type"] not in RELEASE_TYPES:
        raise InvalidMetadataError("Invalid release type.")
    if not metadata["genres"]:
        raise InvalidMetadataError("You must specify at least one genre.")
    if metadata["source"] == "CD" and metadata["year"] < 1982:
        raise InvalidMetadataError("You cannot have a CD upload from before 1982.")
    if metadata["source"] not in SOURCES.values():
        raise InvalidMetadataError(f"{metadata['source']} is not a valid source.")
    if metadata["label"] and (len(metadata["label"]) < 2 or len(metadata["label"]) > 80):
        raise InvalidMetadataError("Label must be over 2 and under 80 characters.")
    if metadata["catno"] and (len(metadata["catno"]) < 2 or len(metadata["catno"]) > 80):
        raise InvalidMetadataError("Catno must be over 2 and under 80 characters.")

    return metadata
