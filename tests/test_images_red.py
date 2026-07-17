import anyio
import pytest

from steak import cfg
from steak.config.validations import ImageUploader as ImageUploaderConfig
from steak.errors import ImageUploadFailed
from steak.images import HOSTS
from steak.images.red import UPLOAD_URL, ImageUploader


class FakeResponse:
    def __init__(self, body):
        self.body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def raise_for_status(self):
        return None

    async def json(self, *, loads):
        return self.body


class FakeSession:
    def __init__(self, body, request):
        self.body = body
        self.request = request

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def post(self, url, *, headers, data):
        self.request.update(url=url, headers=headers, data=data)
        return FakeResponse(self.body)


def test_red_provider_requires_api_key_when_selected() -> None:
    with pytest.raises(ValueError, match="RED image host API key not specified"):
        ImageUploaderConfig(image_uploader="RED", cover_uploader="catbox")

    config = ImageUploaderConfig(
        image_uploader="RED",
        cover_uploader="catbox",
        red_key="image-api-key",
    )
    assert config.red_key == "image-api-key"


def test_red_provider_uploads_file_with_api_key(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "cover.jpg"
    image_path.write_bytes(b"image-data")
    request = {}
    original_key = cfg.image.red_key
    cfg.image.red_key = "image-api-key"

    body = {
        "status": "success",
        "response": {
            "url": "https://redacted.sh/i/oXp3pZzB39g.jpg",
            "thumbUrl": "https://redacted.sh/t/oXp3pZzB39g.jpg",
        },
    }
    monkeypatch.setattr(
        "steak.images.red.aiohttp.ClientSession",
        lambda: FakeSession(body, request),
    )

    try:
        result = anyio.run(ImageUploader().upload_file, str(image_path))
    finally:
        cfg.image.red_key = original_key

    assert result == ("https://redacted.sh/i/oXp3pZzB39g.jpg", None)
    assert request["url"] == UPLOAD_URL
    assert request["headers"] == {
        "Authorization": "image-api-key",
        "User-Agent": cfg.upload.user_agent,
    }
    assert any(field[0].get("name") == "file" for field in request["data"]._fields)
    assert HOSTS["RED"].ImageUploader is ImageUploader


def test_red_provider_rejects_api_failure(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "cover.png"
    image_path.write_bytes(b"image-data")
    monkeypatch.setattr(
        "steak.images.red.aiohttp.ClientSession",
        lambda: FakeSession({"status": "failure"}, {}),
    )

    async def upload() -> None:
        try:
            await ImageUploader().upload_file(str(image_path))
        except ImageUploadFailed as error:
            assert str(error) == "RED image host returned a failure response"
        else:
            raise AssertionError("Expected ImageUploadFailed")

    anyio.run(upload)
