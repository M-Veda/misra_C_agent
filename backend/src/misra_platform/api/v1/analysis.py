import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.core.config import Settings
from misra_platform.core.dependencies import (
    get_database_session,
    get_redis_client,
    get_settings_dependency,
)
from misra_platform.domain.enums.analysis_status import AnalysisRunType, AnalysisStatus
from misra_platform.domain.models.analysis import AnalysisRun, Project, TranslationUnitRecord
from misra_platform.integrations.storage.local import LocalArtifactStorage
from misra_platform.repositories.base import session_scope
from misra_platform.schemas.responses.analysis import (
    AnalysisRunCreateRequest,
    AnalysisRunResponse,
    AstArtifactResponse,
    AstNodeResponse,
    ProjectCreateRequest,
    ProjectResponse,
    TranslationUnitResponse,
)
from misra_platform.services.analysis_orchestrator import AnalysisOrchestrator

router = APIRouter(tags=["Analysis"])


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> Project:
    project = Project(
        name=request.name,
        root_path=request.root_path,
        toolchain_profile_id=request.toolchain_profile_id,
        compile_commands_path=request.compile_commands_path,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> list[Project]:
    result = await session.execute(select(Project).order_by(Project.created_at.desc()))
    return list(result.scalars().all())


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> Project:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post(
    "/projects/{project_id}/analysis/runs",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_analysis_run(
    project_id: uuid.UUID,
    request: AnalysisRunCreateRequest,
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> AnalysisRun:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    run = AnalysisRun(
        project_id=project_id,
        run_type=request.run_type,
        status=AnalysisStatus.QUEUED,
        base_run_id=request.base_run_id,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    async def execute_run() -> None:
        orchestrator = AnalysisOrchestrator(settings, redis)
        async with session_scope() as background_session:
            await orchestrator.run_analysis(
                background_session,
                project_id,
                run.id,
                AnalysisRunType(request.run_type),
                request.base_run_id,
            )

    background_tasks.add_task(execute_run)
    return run


@router.get("/analysis/runs/{run_id}", response_model=AnalysisRunResponse)
async def get_analysis_run(
    run_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AnalysisRun:
    run = await session.get(AnalysisRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")
    return run


@router.get(
    "/analysis/runs/{run_id}/translation-units", response_model=list[TranslationUnitResponse]
)
async def list_translation_units(
    run_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> list[TranslationUnitRecord]:
    result = await session.execute(
        select(TranslationUnitRecord)
        .where(TranslationUnitRecord.analysis_run_id == run_id)
        .order_by(TranslationUnitRecord.file_path.asc())
    )
    return list(result.scalars().all())


@router.get(
    "/analysis/runs/{run_id}/translation-units/{tu_id}/ast",
    response_model=AstArtifactResponse,
)
async def get_translation_unit_ast(
    run_id: uuid.UUID,
    tu_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> AstArtifactResponse:
    record = await session.get(TranslationUnitRecord, tu_id)
    if not record or record.analysis_run_id != run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Translation unit not found"
        )
    if not record.ast_cache_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="AST artifact not available"
        )

    storage = LocalArtifactStorage(settings)
    payload = storage.read_ast_artifact(record.ast_cache_path)

    return AstArtifactResponse(
        translation_unit_id=record.id,
        file_path=record.file_path,
        translation_unit_hash=record.translation_unit_hash or "",
        nodes=[AstNodeResponse.model_validate(node) for node in payload.get("nodes", [])],
        diagnostics=payload.get("diagnostics", []),
        preprocessor=payload.get("preprocessor", {}),
    )


@router.get("/analysis/runs/{run_id}/stream")
async def stream_analysis_progress(
    run_id: uuid.UUID,
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> StreamingResponse:
    async def event_generator():
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"analysis:{run_id}")
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                payload = message["data"]
                if isinstance(payload, bytes):
                    payload = payload.decode("utf-8")
                yield f"event: progress\ndata: {payload}\n\n"
        finally:
            await pubsub.unsubscribe(f"analysis:{run_id}")
            await pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
