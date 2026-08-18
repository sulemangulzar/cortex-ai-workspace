from app.api.dependencies import CurrentUser
from fastapi import APIRouter, File, UploadFile

router = APIRouter(prefix="/project/", tags=["Project Sources"])

@router.post("/{project_id}/sources/upload")
async def upload_sources(user : CurrentUser, file : UploadFile = File()):
    return file.filename
