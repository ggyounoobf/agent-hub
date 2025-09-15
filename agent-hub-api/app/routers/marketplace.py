from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, Form
from fastapi import File as FastAPIFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict
from app.utils.logging import setup_logging
import traceback

from app.services.agent_sync_service import AgentSyncService
from app.database.connection import get_db_session
from app.auth.dependencies import get_current_user
from app.database.models import User, UserRole
from app.models.agent_schemas import (
    AgentRequestResponse,
    AgentResponse,
    AgentOwnershipResponse,
    AgentRequestReview,
    UserAgentStatsResponse
)


logger = setup_logging(__name__)
router = APIRouter(prefix="/marketplace", tags=["Marketplace"])

# Get all available agents for requesting (all agents in the system that user doesn't already own)
@router.get("/agents", response_model=List[AgentResponse])
async def get_available_agents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        current_user_id = str(getattr(current_user, 'id', ''))
        agents = await AgentSyncService.get_available_agents_for_user(current_user_id, db)
        return agents
    except Exception as e:
        logger.error(f"Error fetching available agents: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Get agent by ID (with tools) - only accessible if user owns the agent or is admin
@router.get("/agent/{agent_id}", response_model=AgentResponse)
async def get_agent_by_id(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Check if user owns this agent or is admin
    is_admin = getattr(current_user, "role", None) == UserRole.ADMIN
    if not is_admin:
        current_user_id = str(getattr(current_user, 'id', ''))
        owns_agent = await AgentSyncService.user_owns_agent(current_user_id, agent_id, db)
        if not owns_agent:
            raise HTTPException(status_code=403, detail="Access denied to this agent")
    
    agent = await AgentSyncService.get_agent_by_id(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.get("/owned-agents", response_model=List[AgentOwnershipResponse])
async def get_owned_agents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    try:
        current_user_id = str(getattr(current_user, 'id', ''))
        agents = await AgentSyncService.get_owned_agents(current_user_id, db)
        return agents
    except Exception as e:
        logger.error(f"Error fetching owned agents: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/request-agent/{agent_id}", response_model=Dict[str, str])
async def request_agent(
    agent_id: str,
    justification: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    try:
        current_user_id = str(getattr(current_user, 'id', ''))
        result = await AgentSyncService.request_agent_ownership(current_user_id, agent_id, db, justification)
        return result
    except Exception as e:
        logger.error(f"Error requesting agent ownership: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Get all requests made by the current user
@router.get("/my-requests", response_model=List[AgentRequestResponse])
async def get_my_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    current_user_id = str(getattr(current_user, 'id', ''))
    requests = await AgentSyncService.get_agent_requests(current_user_id, db)
    return requests

# Get all pending requests (admin only)
@router.get("/pending-requests", response_model=List[AgentRequestResponse])
async def get_pending_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    if getattr(current_user, "role", None) != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    requests = await AgentSyncService.get_pending_requests(db)
    return requests

# Review an agent ownership request (admin only)
@router.post("/review-request/{request_id}", response_model=Dict)
async def review_agent_request(
    request_id: str,
    action: str = Form(...),  # "approve" or "reject"
    reason: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    if getattr(current_user, "role", None) != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    current_user_id = str(getattr(current_user, 'id', ''))
    result = await AgentSyncService.review_agent_request(request_id, action, current_user_id, db, reason)
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

# Bulk review requests (admin only)
@router.post("/bulk-review", response_model=Dict)
async def bulk_review_requests(
    request_ids: List[str] = Form(...),
    action: str = Form(...),
    reason: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    if getattr(current_user, "role", None) != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    current_user_id = str(getattr(current_user, 'id', ''))
    result = await AgentSyncService.bulk_review_requests(request_ids, action, current_user_id, db, reason)
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

# Revoke agent ownership (admin only)
@router.post("/revoke-ownership", response_model=Dict)
async def revoke_agent_ownership(
    user_id: str = Form(...),
    agent_id: str = Form(...),
    reason: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    if getattr(current_user, "role", None) != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    current_user_id = str(getattr(current_user, 'id', ''))
    result = await AgentSyncService.revoke_agent_ownership(user_id, agent_id, current_user_id, db, reason)
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

# Get user agent stats
@router.get("/user-agent-stats", response_model=UserAgentStatsResponse)
async def get_user_agent_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    current_user_id = str(getattr(current_user, 'id', ''))
    stats = await AgentSyncService.get_user_agent_stats(current_user_id, db)
    return stats