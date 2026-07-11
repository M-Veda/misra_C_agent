"""Phase 4 deliverable: CFG visualization API.

Reuses the AST artifacts already cached to disk during analysis (see
`analysis.py`'s `.../ast` endpoint for the equivalent AST-only access
pattern) to build and expose real basic-block control-flow graphs for
review/debugging UIs, without re-running any analysis.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.core.config import Settings
from misra_platform.core.dependencies import get_database_session, get_settings_dependency
from misra_platform.domain.models.analysis import TranslationUnitRecord
from misra_platform.schemas.responses.cfg import (
    CfgFunctionListResponse,
    ControlFlowGraphResponse,
)
from misra_platform.services.cfg_service import (
    AstArtifactUnavailableError,
    CfgService,
    FunctionNotFoundError,
)

router = APIRouter(tags=["CFG"])


async def _load_translation_unit(
    session: AsyncSession, run_id: uuid.UUID, tu_id: uuid.UUID
) -> TranslationUnitRecord:
    record = await session.get(TranslationUnitRecord, tu_id)
    if not record or record.analysis_run_id != run_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Translation unit not found")
    return record


@router.get(
    "/analysis/runs/{run_id}/translation-units/{tu_id}/functions",
    response_model=CfgFunctionListResponse,
)
async def list_translation_unit_functions(
    run_id: uuid.UUID,
    tu_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> CfgFunctionListResponse:
    record = await _load_translation_unit(session, run_id, tu_id)
    service = CfgService(settings)
    try:
        functions = service.list_functions(record)
    except AstArtifactUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return CfgFunctionListResponse(translation_unit_id=str(tu_id), functions=functions)


@router.get(
    "/analysis/runs/{run_id}/translation-units/{tu_id}/functions/{function_node_id}/cfg",
    response_model=ControlFlowGraphResponse,
)
async def get_function_cfg(
    run_id: uuid.UUID,
    tu_id: uuid.UUID,
    function_node_id: str,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
    include_dot: Annotated[bool, Query(description="Also include a Graphviz DOT rendering")] = False,
) -> ControlFlowGraphResponse:
    record = await _load_translation_unit(session, run_id, tu_id)
    service = CfgService(settings)
    try:
        cfg = service.build_cfg(record, function_node_id)
    except AstArtifactUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except FunctionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    payload = cfg.to_dict()
    if include_dot:
        payload["dot"] = cfg.to_dot()
    return ControlFlowGraphResponse.model_validate(payload)
