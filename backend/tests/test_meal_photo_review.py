"""Unit safety coverage for the non-nutrition meal-photo review fallback."""

from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image
from pydantic import ValidationError

from app.modules.nutrition.schemas import MealPhotoCommentRequest
from app.modules.nutrition.service import normalize_meal_photo
from app.modules.nutrition.storage import MealPhotoStorageError, S3MealPhotoStorage


def _settings(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "meal_photo_max_bytes": 1024 * 1024,
        "meal_photo_max_pixels": 1_000_000,
        "s3_bucket": "synthetic-test",
        "s3_endpoint_url": "http://unused",
        "s3_access_key_id": "unused",
        "s3_secret_access_key": "unused",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _png() -> bytes:
    output = BytesIO()
    Image.new("RGBA", (16, 12), (20, 40, 60, 120)).save(output, format="PNG")
    return output.getvalue()


def test_meal_photo_is_reencoded_to_jpeg_without_retaining_png_metadata() -> None:
    normalized = normalize_meal_photo(_png(), "image/png", _settings())

    assert normalized.content_type == "image/jpeg"
    assert normalized.image.startswith(b"\xff\xd8")
    assert len(normalized.sha256_hex) == 64
    with Image.open(BytesIO(normalized.image)) as image:
        assert image.format == "JPEG"
        assert image.getexif() == {}


@pytest.mark.parametrize(
    ("payload", "content_type", "message"),
    [
        (b"not an image", "image/jpeg", "corrupt or unsupported"),
        (_png(), "image/gif", "Only JPEG and PNG"),
        (b"", "image/jpeg", "empty"),
    ],
)
def test_meal_photo_rejects_unsupported_or_corrupt_data(
    payload: bytes, content_type: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        normalize_meal_photo(payload, content_type, _settings())


def test_meal_photo_rejects_too_many_pixels() -> None:
    with pytest.raises(ValueError, match="too many pixels"):
        normalize_meal_photo(_png(), "image/png", _settings(meal_photo_max_pixels=10))


def test_blank_physician_comment_is_rejected_before_database_write() -> None:
    with pytest.raises(ValidationError, match="Comment cannot be blank"):
        MealPhotoCommentRequest(body="   ")


def test_storage_provider_errors_are_opaque() -> None:
    class BrokenClient:
        def put_object(self, **kwargs: object) -> None:
            raise RuntimeError("endpoint leaked.example.invalid")

    storage = S3MealPhotoStorage(_settings(), client=BrokenClient())
    with pytest.raises(MealPhotoStorageError, match="temporarily unavailable") as error:
        storage.put("opaque-key", b"image")
    assert "leaked" not in str(error.value)
