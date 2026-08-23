from __future__ import annotations

import contextlib
from typing import Any

import aioboto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.core.exceptions import StorageError


class StorageService:
    def __init__(self) -> None:
        settings.validate_storage_settings()
        self.bucket_name = settings.BUCKET_NAME
        self.session = aioboto3.Session()

    @contextlib.asynccontextmanager
    async def _client(self):
        client_context: Any = self.session.client(
            "s3",
            endpoint_url=settings.SUPABASE_S3_ENDPOINT,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        async with client_context as client:
            yield client

    async def upload_bytes(self, object_key: str, data: bytes, content_type: str | None) -> None:
        try:
            async with self._client() as client:
                await client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    Body=data,
                    ContentType=content_type or "application/octet-stream",
                )
        except (BotoCoreError, ClientError, RuntimeError) as exc:
            raise StorageError(f"Failed to upload file: {exc}") from exc

    async def delete_object(self, object_key: str) -> None:
        try:
            async with self._client() as client:
                await client.delete_object(Bucket=self.bucket_name, Key=object_key)
        except (BotoCoreError, ClientError, RuntimeError) as exc:
            raise StorageError(f"Failed to remove file: {exc}") from exc

    async def delete_prefix(self, prefix: str) -> None:
        try:
            async with self._client() as client:
                continuation_token = None
                while True:
                    kwargs = {"Bucket": self.bucket_name, "Prefix": prefix}
                    if continuation_token:
                        kwargs["ContinuationToken"] = continuation_token
                    response = await client.list_objects_v2(**kwargs)
                    objects = [{"Key": item["Key"]} for item in response.get("Contents", [])]
                    if objects:
                        await client.delete_objects(Bucket=self.bucket_name, Delete={"Objects": objects})
                    if not response.get("IsTruncated"):
                        break
                    continuation_token = response.get("NextContinuationToken")
        except (BotoCoreError, ClientError, RuntimeError) as exc:
            raise StorageError(f"Failed to remove project files: {exc}") from exc
