import asyncio
from pathlib import Path
import shutil

class WrokSpaceService:
    def __init__(self, base_dir: str | Path = "tmp/context") -> None:
        self.base_dir = Path(base_dir)

    async def create(self, run_id : str) -> Path:
        workspace = self.base_dir / run_id
        repo = workspace / "repo"

        await asyncio.to_thread(
            workspace.mkdir,
            parents=True,
            exist_ok=False
        )
        await asyncio.to_thread(
            repo.mkdir,
            parents=True,
            exist_ok=False
        )
        return workspace

    def get_repo_path(self, run_id: str) -> Path:
            return self.base_dir / run_id / "repo"

    def get_input_zip_path(self, run_id: str) -> Path:
            return self.base_dir / run_id / "input.zip"

    async def delete(self, run_id: str) -> None:
            workspace = self.base_dir / run_id

            if workspace.exists():
                await asyncio.to_thread(
                    shutil.rmtree,
                    workspace,
                )
