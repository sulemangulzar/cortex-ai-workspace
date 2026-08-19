import asyncio
from pathlib import Path
import shutil
from posix import mkdir

class WrokSpaceService:
    def __init__(self, base_dir: str ="tmp/contex") -> None:
        self.base_dir = base_dir

    async def create(self, run_id : str) -> Path:
        workspace = self.base_dir / run_id
        repo = self.base_dir / "repo"

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
