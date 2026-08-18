from pathlib import Path


class StorageService:

    def __init__(self, s3):
        self.s3 = s3

    async def upload_fileobj(
        self,
        fileobj,
        bucket: str,
        key: str,
    ):
        fileobj.seek(0)

        await self.s3.upload_fileobj(
            fileobj,
            bucket,
            key,
        )

    async def upload_path(
        self,
        path: Path,
        bucket: str,
        key: str,
    ):
        with path.open("rb") as file:
            await self.s3.upload_fileobj(
                file,
                bucket,
                key,
            )

    async def download_to_path(
        self,
        bucket: str,
        key: str,
        path: Path,
    ):
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open("wb") as file:
            await self.s3.download_fileobj(
                bucket,
                key,
                file,
            )
