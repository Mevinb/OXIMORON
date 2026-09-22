from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse

from apps.backend.dependencies import verify_bearer_token
from core.contracts.errors import ErrorCode, OximoronException
from core.contracts.models import (
    GenerationDescriptor,
    ImageGenerationRequest,
)
from core.services.generation_service import GenerationService

router = APIRouter(tags=["Generations & Artifacts"])

def get_generation_service(request: Request) -> GenerationService:
    return request.app.state.generation_service

@router.post("/generate/image", response_model=GenerationDescriptor)
async def generate_image(
    req: ImageGenerationRequest,
    _token: str = Depends(verify_bearer_token),
    gen_svc: GenerationService = Depends(get_generation_service),
):
    return await gen_svc.generate_image(req)

@router.get("/generations", response_model=list[GenerationDescriptor])
async def list_generations(
    _token: str = Depends(verify_bearer_token),
    gen_svc: GenerationService = Depends(get_generation_service),
    limit: int = Query(default=50, ge=1, le=100),
):
    return await gen_svc.list_generations(limit=limit)

@router.get("/artifacts/{artifact_id}/content")
async def get_artifact_content(
    artifact_id: str,
    _token: str = Depends(verify_bearer_token),
    gen_svc: GenerationService = Depends(get_generation_service),
):
    artifact = await gen_svc.get_artifact(artifact_id)
    path = Path(artifact.absolute_path)
    if not path.exists():
        raise OximoronException(
            code=ErrorCode.NOT_FOUND,
            message=f"Artifact file not found on disk: {artifact.relative_path}",
            status_code=404,
        )
    return FileResponse(
        path=str(path),
        media_type=artifact.media_type,
        filename=artifact.relative_path,
    )
