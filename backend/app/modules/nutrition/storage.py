"""Private S3-compatible storage boundary for re-encoded meal photographs."""

from functools import lru_cache
from typing import Any, Protocol

import boto3  # type: ignore[import-untyped]
from botocore.config import Config  # type: ignore[import-untyped]

from app.core.config import Settings, get_settings


class MealPhotoStorageError(RuntimeError):
    """A safe, opaque storage failure exposed to the API boundary."""


class MealPhotoStorage(Protocol):
    def put(self, key: str, image: bytes) -> None: ...

    def read(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


class S3MealPhotoStorage:
    """S3-compatible object store client; never returns a public object URL."""

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self._bucket = settings.s3_bucket
        self._client = client or boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            config=Config(s3={"addressing_style": "path"}),
        )

    def put(self, key: str, image: bytes) -> None:
        try:
            # The local SeaweedFS S3 endpoint starts empty. Creating the configured private
            # bucket is idempotent for the local demo; deployment credentials may instead point
            # at a pre-provisioned bucket.
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except Exception:
                self._client.create_bucket(Bucket=self._bucket)
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=image,
                ContentType="image/jpeg",
                ACL="private",
            )
        except Exception as exc:  # Provider errors are intentionally not exposed to users.
            raise MealPhotoStorageError("Meal photo storage is temporarily unavailable") from exc

    def read(self, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return bytes(response["Body"].read())
        except Exception as exc:  # Provider errors are intentionally not exposed to users.
            raise MealPhotoStorageError("Meal photo storage is temporarily unavailable") from exc

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except Exception:
            # The object is private and unreachable without its database reference.  A later
            # retention/cleanup job can reclaim an orphan; do not hide the original DB failure.
            return


@lru_cache
def get_meal_photo_storage() -> S3MealPhotoStorage:
    return S3MealPhotoStorage(get_settings())
