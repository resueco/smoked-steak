from html import unescape
from typing import TYPE_CHECKING

import asyncclick as click

from steak import cfg
from steak.errors import RequestError, UploadError

if TYPE_CHECKING:
    from steak.trackers.base import BaseGazelleApi


def print_preassumptions(
    gazelle_site: "BaseGazelleApi",
    path: str,
    group_id: int | None,
    source: str | None,
    encoding: str | None,
) -> None:
    """Print what all the passed CLI options will do.

    Args:
        gazelle_site: The tracker API instance.
        path: Path to the album folder.
        group_id: Optional existing group ID.
        source: Media source.
        encoding: Audio encoding tuple.
    """
    click.secho(f"\nProcessing {path}", fg="cyan", bold=True)
    second = []
    if source:
        second.append(f"from {source}")
    if encoding:
        second.append(f"as {encoding}")
    if second:
        click.secho(f"Uploading {' '.join(second)}.", fg="yellow")


async def confirm_group_upload(gazelle_site: "BaseGazelleApi", group_id: int, source: str | None) -> None:
    """Confirm upload to existing group.

    Args:
        gazelle_site: The tracker API instance.
        group_id: The torrent group ID.
        source: Media source filter.
    """
    await print_group_info(gazelle_site, group_id, source)
    click.confirm(
        click.style("\nWould you like to continue to upload to this group?", fg="magenta"),
        default=True,
        abort=True,
    )


async def print_group_info(gazelle_site: "BaseGazelleApi", group_id: int, source: str | None) -> None:
    """Print information about the torrent group that was passed as a CLI argument.

    Also print all the torrents that are in that group.

    Args:
        gazelle_site: The tracker API instance.
        group_id: The torrent group ID.
        source: Media source filter.
    """
    try:
        group = await gazelle_site.torrentgroup(group_id)
    except RequestError as err:
        raise UploadError("Could not get information about torrent group from RED.") from err

    artists = [a["name"] for a in group["group"]["musicInfo"]["artists"]]
    artists = ", ".join(artists) if len(artists) < 4 else cfg.upload.formatting.various_artist_word
    click.secho(
        f"\nTorrents matching source {source} in (Group {group_id}) {artists} - {group['group']['name']}:",
        fg="yellow",
        bold=True,
    )

    for t in group["torrents"]:
        if t["media"] == source:
            if t["remastered"]:
                click.echo(
                    unescape(
                        f"> {t['remasterYear']} / {t['remasterRecordLabel']} / "
                        f"{t['remasterCatalogueNumber']} / {t['format']} / "
                        f"{t['encoding']}"
                    )
                )
            if not t["remastered"]:
                click.echo(
                    unescape(
                        f"> OR / {group['group']['recordLabel']} / "
                        f"{group['group']['catalogueNumber']} / {t['format']} / "
                        f"{t['encoding']}"
                    )
                )
