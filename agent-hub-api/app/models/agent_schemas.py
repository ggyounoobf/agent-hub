from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AgentRequestBase(BaseModel):
    agent_id: str
    justification: Optional[str] = None


class AgentRequestCreate(AgentRequestBase):
    pass


class AgentRequestResponse(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    agent_description: Optional[str] = None
    agent_tools: List[dict]
    status: str
    justification: Optional[str] = None
    review_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgentRequestReview(BaseModel):
    action: str  # "approve" or "reject"
    reason: Optional[str] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    tools: List[dict]


class AgentOwnershipResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    tools: List[dict]


class UserAgentStatsResponse(BaseModel):
    user_id: str
    owned_agents: int
    pending_requests: int
    approved_requests: int
    rejected_requests: int
    total_requests: int