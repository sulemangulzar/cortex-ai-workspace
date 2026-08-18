from collections.abc import AsyncIterator
from typing import Any, cast

import aioboto3

from app.core.config import settings


class S3Config:
    def __init__(self):
        self.session = aioboto3.Session()

    async def get_client(self) -> AsyncIterator[Any]:
        client_context = cast(
            Any,
            self.session.client(
                "s3",
                endpoint_url=settings.SUPABASE_S3_ENDPOINT,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name="ap-southeast-2",
            ),
        )
        async with client_context as client:
            yield client

s3_config = S3Config()
