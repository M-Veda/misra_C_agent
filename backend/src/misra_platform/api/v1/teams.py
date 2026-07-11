import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.core.dependencies import get_database_session
from misra_platform.domain.models.enterprise import TeamMemberRecord, TeamRecord
from misra_platform.repositories.enterprise_repo import EnterpriseRepository
from misra_platform.schemas.requests.enterprise import AddTeamMemberRequest, CreateTeamRequest
from misra_platform.schemas.responses.enterprise import TeamMemberResponse, TeamResponse

router = APIRouter(tags=["Teams"])


@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    request: CreateTeamRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TeamResponse:
    repo = EnterpriseRepository(session)
    team = await repo.create_team(
        TeamRecord(name=request.name, description=request.description)
    )
    await session.commit()
    return TeamResponse.model_validate(team)


@router.get("/teams", response_model=list[TeamResponse])
async def list_teams(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> list[TeamResponse]:
    repo = EnterpriseRepository(session)
    teams = await repo.list_teams()
    responses: list[TeamResponse] = []
    for team in teams:
        members = await repo.list_team_members(team.id)
        response = TeamResponse.model_validate(team)
        response.members = [TeamMemberResponse.model_validate(m) for m in members]
        responses.append(response)
    return responses


@router.get("/teams/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TeamResponse:
    repo = EnterpriseRepository(session)
    team = await repo.get_team(team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    members = await repo.list_team_members(team.id)
    response = TeamResponse.model_validate(team)
    response.members = [TeamMemberResponse.model_validate(m) for m in members]
    return response


@router.post(
    "/teams/{team_id}/members",
    response_model=TeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_team_member(
    team_id: uuid.UUID,
    request: AddTeamMemberRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TeamMemberResponse:
    repo = EnterpriseRepository(session)
    team = await repo.get_team(team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    member = await repo.add_team_member(
        TeamMemberRecord(
            team_id=team_id,
            user_id=request.user_id,
            display_name=request.display_name,
            email=request.email,
            role=request.role,
        )
    )
    await session.commit()
    return TeamMemberResponse.model_validate(member)
