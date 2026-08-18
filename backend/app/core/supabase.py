from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, BinaryIO, cast

import aioboto3

from app.core.config import settings


class S3Config:
    def __init__(self):
        self.session = aioboto3.Session()

    @asynccontextmanager
    async def get_client(self) -> AsyncIterator[Any]:
        client_context = cast(
            Any,
            self.session.client(
                "s3",
                endpoint_url=settings.SUPABASE_S3_ENDPOINT,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            ),
        )
        async with client_context as client:
            yield client

    async def upload_fileobj(
        self,
        fileobj: BinaryIO,
        bucket: str,
        object_path: str,
        content_type: str | None = None,
    ) -> None:
        settings.validate_storage_settings()
        extra_args = {"ContentType": content_type} if content_type else None
        async with self.get_client() as client:
            await client.upload_fileobj(
                fileobj,
                bucket,
                object_path,
                ExtraArgs=extra_args,
            )

    async def delete_object(self, bucket: str, object_path: str) -> None:
        settings.validate_storage_settings()
        async with self.get_client() as client:
            await client.delete_object(Bucket=bucket, Key=object_path)


s3_config = S3Config()
