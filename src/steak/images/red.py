from pathlib import Path

import aiohttp
import anyio
import msgspec
from aiolimiter import AsyncLimiter

from steak import cfg
from steak.errors import ImageUploadFailed
from steak.images.base import BaseImageUploader

UPLOAD_URL = "https://redacted.sh/ajax.php?action=upload_image"


class ImageUploader(BaseImageUploader):
    """Image uploader for RED's internal image host."""

    def __init__(self) -> None:
        # RED permits up to ten API-key requests per ten seconds.
        self._rate_limiter = AsyncLimiter(10, 10)

    async def upload_file(self, filename: str) -> tuple[str, None]:
        """Upload a local image using RED's API-key-only endpoint."""
        async with await anyio.open_file(filename, "rb") as f:
            file_data = await f.read()

        data = aiohttp.FormData()
        data.add_field("file", file_data, filename=Path(filename).name)
        headers = {
            "Authorization": cfg.image.red_key or "",
            "User-Agent": cfg.upload.user_agent,
        }

        try:
            async with (
                self._rate_limiter,
                aiohttp.ClientSession() as session,
                session.post(UPLOAD_URL, headers=headers, data=data) as resp,
            ):
                resp.raise_for_status()
                response = await resp.json(loads=msgspec.json.decode)
                if response.get("status") != "success":
                    raise ImageUploadFailed("RED image host returned a failure response")
                return response["response"]["url"], None
        except ImageUploadFailed:
            raise
        except (msgspec.DecodeError, KeyError, TypeError, AttributeError) as e:
            raise ImageUploadFailed(f"Failed decoding body: {e}") from e
        except aiohttp.ClientError as e:
            raise ImageUploadFailed(f"Network error: {e}") from e
