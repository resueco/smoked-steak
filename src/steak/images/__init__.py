import asyncio
from typing import Any

import asyncclick as click
import pyperclip

from steak import cfg
from steak.common import AliasedCommands, commandgroup
from steak.errors import ImageUploadFailed
from steak.images import catbox, imgbb, imgbox, oeimg, ptpimg, ptscreens

HOSTS = {
    "ptpimg": ptpimg,
    "catbox": catbox,
    "ptscreens": ptscreens,
    "oeimg": oeimg,
    "imgbb": imgbb,
    "imgbox": imgbox,
}


def validate_image_host(ctx: click.Context, param: click.Parameter, value: str) -> Any:
    """Validate and return the image host module.

    Args:
        ctx: Click context.
        param: Click parameter.
        value: The image host name.

    Returns:
        The image host module.

    Raises:
        click.BadParameter: If the image host is invalid.
    """
    try:
        return HOSTS[value]
    except KeyError:
        raise click.BadParameter(f"{value} is not a valid image host") from None


@commandgroup.group(cls=AliasedCommands)
async def images() -> None:
    """Create and manage uploads to image hosts."""
    pass


@images.command()
@click.argument(
    "filepaths",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    nargs=-1,
)
@click.option(
    "--image-host",
    "-i",
    help="The name of the image host to upload to",
    default=cfg.image.image_uploader,
    callback=validate_image_host,
)
async def up(filepaths: tuple[str, ...], image_host: Any) -> None:
    """Upload images to an image host."""
    await upload_images(filepaths, image_host)


async def upload_images(filepaths: tuple, image_host) -> list[str]:
    """Upload images to the specified host asynchronously.

    Args:
        filepaths: Tuple of file paths to upload.
        image_host: The image host module.

    Returns:
        List of uploaded URLs.
    """
    urls = []
    uploader = image_host.ImageUploader()
    try:
        tasks = [uploader.upload_file(f) for f in filepaths]
        for url, _deletion_url in await asyncio.gather(*tasks):
            click.secho(url)
            urls.append(url)
        if cfg.upload.description.copy_uploaded_url_to_clipboard:
            pyperclip.copy("\n".join(urls))
        return urls
    except (ImageUploadFailed, ValueError) as error:
        click.secho(f"Image Upload Failed. {error}", fg="red")
        raise ImageUploadFailed("Failed to upload image") from error


async def upload_cover(cover_path: str | None) -> str | None:
    """Upload cover image to the configured image host.

    Args:
        cover_path: Path to the cover image file.

    Returns:
        The uploaded image URL, or None if upload failed.
    """
    if not cover_path:
        click.secho("\nNo Cover Image Path was provided to upload...", fg="red", nl=False)
        return None
    click.secho(f"Uploading cover to {cfg.image.cover_uploader}...", fg="yellow", nl=False)
    try:
        uploader = HOSTS[cfg.image.cover_uploader].ImageUploader()
        url, _ = await uploader.upload_file(cover_path)
        click.secho(f" done! {url}", fg="yellow")
        return url
    except (ImageUploadFailed, ValueError) as error:
        click.secho(f" failed :( {error}", fg="red")
        return None
