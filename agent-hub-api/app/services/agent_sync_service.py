from typing import Dict, Optional
from llama_index.core.agent.workflow import ReActAgent
from app.agents.agent_builders import AgentInfo  # Import AgentInfo
from app.database.models import Agent, AgentRequest, AgentTool, AgentOwnership
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import uuid
from enum import Enum

class RequestStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class AgentSyncService:
    @staticmethod
    async def sync_agents_to_db(
        agents: Dict[str, AgentInfo],  # Updated type annotation
        db: AsyncSession
    ):
        """Sync agents and their tools to the database"""
        try:
            for agent_name, agent_info in agents.items():  # Updated variable name
                # Check if agent exists
                result = await db.execute(select(Agent).where(Agent.name == agent_name))
                db_agent = result.scalar_one_or_none()
                
                if not db_agent:
                    # Create new agent with description
                    db_agent = Agent(
                        id=str(uuid.uuid4()), 
                        name=agent_name,
                        description=agent_info.description
                    )
                    db.add(db_agent)
                    await db.flush()
                else:
                    # Update existing agent description if it's different
                    if db_agent.description != agent_info.description:
                        db_agent.description = agent_info.description
                
                # Add tools (access tools from AgentInfo)
                for tool in agent_info.tools:  # Use agent_info.tools instead of getattr
                    tool_name = getattr(getattr(tool, "metadata", None), "name", "unknown")
                    tool_description = getattr(getattr(tool, "metadata", None), "description", "")
                    
                    result = await db.execute(
                        select(AgentTool).where(
                            and_(
                                AgentTool.name == tool_name,
                                AgentTool.agent_id == db_agent.id
                            )
                        )
                    )
                    db_tool = result.scalar_one_or_none()
                    if not db_tool:
                        db.add(AgentTool(
                            name=tool_name, 
                            agent_id=db_agent.id,                            
                            # TODO: Temporary commented
                            # description=tool_description  # Add tool description if your model supports it
                        ))
            
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise e

    @staticmethod
    async def get_available_agents(db: AsyncSession) -> list[dict]:
        """Get all available agents"""
        result = await db.execute(
            select(Agent).options(selectinload(Agent.tools))  # Eagerly load tools
        )
        agents = result.scalars().all()

        agents_list = []
        for agent in agents:
            agents_list.append({
                "id": agent.id,
                "name": agent.name,
                "description": getattr(agent, "description", ""),
                "tools": [{"id": tool.id, "name": tool.name} for tool in agent.tools]
            })
        
        return agents_list

    @staticmethod
    async def get_available_agents_for_user(user_id: str, db: AsyncSession) -> list[dict]:
        """Get all available agents including rejected ones for re-appeal"""
        # Get all agents with their tools
        result = await db.execute(
            select(Agent).options(selectinload(Agent.tools))  # Eagerly load tools
        )
        all_agents = result.scalars().all()
        
        # Get user's owned agents
        owned_result = await db.execute(
            select(AgentOwnership).where(AgentOwnership.user_id == user_id)
        )
        owned_agents = owned_result.scalars().all()
        owned_agent_ids = {str(ownership.agent_id) for ownership in owned_agents}  # Convert to string

        # Return all agents (including rejected ones for re-appeal, but excluding owned ones)
        agents_list = []
        for agent in all_agents:
            if str(agent.id) not in owned_agent_ids:  # Convert to string for comparison
                agents_list.append({
                    "id": agent.id,
                    "name": agent.name,
                    "description": getattr(agent, "description", ""),
                    "tools": [{"id": tool.id, "name": tool.name} for tool in agent.tools]
                })
        
        return agents_list

    @staticmethod
    async def get_agent_by_name(db: AsyncSession, agent_name: str) -> Optional[dict]:
        """Get agent by name with tools"""
        result = await db.execute(
            select(Agent).where(Agent.name == agent_name).options(selectinload(Agent.tools))
        )
        agent = result.scalar_one_or_none()
        if not agent:
            return None
        
        return {
            "id": agent.id,
            "name": agent.name,
            "description": getattr(agent, "description", ""),  # Include description
            "tools": [{"id": tool.id, "name": tool.name} for tool in agent.tools]
        }

    @staticmethod
    async def get_owned_agents(user_id: str, db: AsyncSession) -> list[dict]:
        """Get agents owned by a specific user"""
        result = await db.execute(
            select(Agent)
            .join(AgentOwnership)
            .where(AgentOwnership.user_id == user_id)
            .options(selectinload(Agent.tools))  # Eagerly load tools
        )
        agents = result.scalars().all()
        
        agents_list = []
        for agent in agents:
            agents_list.append({
                "id": agent.id,
                "name": agent.name,
                "description": getattr(agent, "description", ""),  # Include description
                "tools": [{"id": tool.id, "name": tool.name} for tool in agent.tools]
            })
        
        return agents_list

    @staticmethod
    async def request_agent_ownership(user_id: str, agent_id: str, db: AsyncSession, justification: Optional[str] = None) -> dict:
        """Request ownership of an agent"""
        try:
            # Check if agent exists
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                return {"status": "error", "message": "Agent not found"}

            # Check if user already owns this agent
            result = await db.execute(
                select(AgentOwnership).where(
                    and_(
                        AgentOwnership.user_id == user_id,
                        AgentOwnership.agent_id == agent_id
                    )
                )
            )
            existing_ownership = result.scalar_one_or_none()
            if existing_ownership:
                return {"status": "error", "message": "User already owns this agent"}

            # Check if request already exists and is pending
            result = await db.execute(
                select(AgentRequest).where(
                    and_(
                        AgentRequest.user_id == user_id,
                        AgentRequest.agent_id == agent_id,
                        AgentRequest.status == RequestStatus.PENDING.value
                    )
                )
            )
            existing_request = result.scalar_one_or_none()
            if existing_request:
                return {"status": "already_requested", "request_id": existing_request.id}

            # Check if there's a previously rejected request and allow re-request
            result = await db.execute(
                select(AgentRequest).where(
                    and_(
                        AgentRequest.user_id == user_id,
                        AgentRequest.agent_id == agent_id,
                        AgentRequest.status == RequestStatus.REJECTED.value
                    )
                )
            )
            rejected_request = result.scalar_one_or_none()
            if rejected_request:
                # Allow re-request by creating a new request
                pass  # Continue to create new request

            # Create new request
            new_request = AgentRequest(
                id=str(uuid.uuid4()),
                user_id=user_id,
                agent_id=agent_id,
                justification=justification,
                status=RequestStatus.PENDING.value
            )
            db.add(new_request)
            await db.commit()
            
            return {
                "status": "success",
                "request_id": new_request.id,
                "message": "Request submitted successfully"
            }
        except Exception as e:
            await db.rollback()
            return {"status": "error", "message": str(e)}

    @staticmethod
    async def get_agent_by_id(db: AsyncSession, agent_id: str) -> Optional[dict]:
        """Get agent by ID with tools"""
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id).options(selectinload(Agent.tools))
        )
        agent = result.scalar_one_or_none()
        if not agent:
            return None
        
        return {
            "id": agent.id,
            "name": agent.name,
            "description": getattr(agent, "description", ""),  # Include description
            "tools": [{"id": tool.id, "name": tool.name} for tool in agent.tools]
        }

    @staticmethod
    async def get_agent_requests(user_id: str, db: AsyncSession) -> list[dict]:
        """Get all requests made by a user"""
        result = await db.execute(
            select(AgentRequest, Agent).join(Agent).options(selectinload(Agent.tools)).where(AgentRequest.user_id == user_id)
        )
        requests = result.all()
        
        return [
            {
                "id": req[0].id,  # Access AgentRequest from tuple
                "agent_id": req[0].agent_id,
                "agent_name": req[1].name,  # Access Agent from tuple
                "agent_description": getattr(req[1], "description", ""),  # Include description
                "agent_tools": [{"id": tool.id, "name": tool.name} for tool in req[1].tools],  # Include tools
                "status": req[0].status,
                "justification": req[0].justification,
                "review_reason": req[0].review_reason,  # Include rejection/approval reason
                "created_at": getattr(req[0], 'created_at', None),
                "updated_at": getattr(req[0], 'updated_at', None)
            }
            for req in requests
        ]

    @staticmethod
    async def get_pending_requests(db: AsyncSession) -> list[dict]:
        """Get all pending requests (for admin/reviewer use)"""
        result = await db.execute(
            select(AgentRequest, Agent).join(Agent).options(selectinload(Agent.tools)).where(
                AgentRequest.status == RequestStatus.PENDING.value
            )
        )
        requests = result.all()
        
        return [
            {
                "id": req[0].id,  # Access AgentRequest from tuple
                "user_id": req[0].user_id,
                "agent_id": req[0].agent_id,
                "agent_name": req[1].name,  # Access Agent from tuple
                "agent_description": getattr(req[1], "description", ""),  # Include description
                "agent_tools": [{"id": tool.id, "name": tool.name} for tool in req[1].tools],  # Include tools
                "status": req[0].status,
                "justification": req[0].justification,
                "review_reason": req[0].review_reason,
                "created_at": getattr(req[0], 'created_at', None)
            }
            for req in requests
        ]

    @staticmethod
    async def review_agent_request(
        request_id: str, 
        action: str, 
        reviewer_id: str, 
        db: AsyncSession,
        reason: Optional[str] = None
    ) -> dict:
        """Review an agent ownership request (approve or reject)"""
        try:
            # Validate action
            if action not in ["approve", "reject"]:
                return {"status": "error", "message": "Invalid action. Must be 'approve' or 'reject'"}
            
            # Get the request with proper eager loading
            result = await db.execute(
                select(AgentRequest).where(AgentRequest.id == request_id)
            )
            agent_request = result.scalar_one_or_none()
            
            if not agent_request:
                return {"status": "error", "message": "Request not found"}
            
            # Check if request is still pending
            current_status = str(agent_request.status)
            if current_status != RequestStatus.PENDING.value:
                return {
                    "status": "error", 
                    "message": f"Request already {current_status}"
                }
            
            # Update request status and reviewer info
            setattr(agent_request, 'reviewed_by', reviewer_id)
            
            if action == "approve":
                setattr(agent_request, 'status', RequestStatus.APPROVED.value)
                
                # Create ownership record
                ownership = AgentOwnership(
                    id=str(uuid.uuid4()),
                    user_id=agent_request.user_id,
                    agent_id=agent_request.agent_id,
                    granted_by=reviewer_id
                )
                db.add(ownership)
                
                message = "Request approved and ownership granted"
            else:  # reject
                setattr(agent_request, 'status', RequestStatus.REJECTED.value)
                if reason:
                    setattr(agent_request, 'review_reason', reason)
                message = f"Request rejected{f': {reason}' if reason else ''}"
            
            # Explicitly mark the object as modified
            await db.flush()
            await db.commit()
            
            return {
                "status": "success",
                "message": message,
                "request_id": request_id,
                "action": action
            }
            
        except IntegrityError as e:
            await db.rollback()
            return {
                "status": "error", 
                "message": "Database integrity error - user may already own this agent"
            }
        except Exception as e:
            await db.rollback()
            return {"status": "error", "message": str(e)}

    @staticmethod
    async def bulk_review_requests(
        request_ids: list[str], 
        action: str, 
        reviewer_id: str, 
        db: AsyncSession,
        reason: Optional[str] = None
    ) -> dict:
        """Review multiple requests at once"""
        try:
            if action not in ["approve", "reject"]:
                return {"status": "error", "message": "Invalid action"}
            
            results = []
            for request_id in request_ids:
                result = await AgentSyncService.review_agent_request(
                    request_id, action, reviewer_id, db, reason
                )
                results.append({"request_id": request_id, "result": result})
            
            return {
                "status": "success",
                "message": f"Processed {len(request_ids)} requests",
                "results": results
            }
        except Exception as e:
            await db.rollback()
            return {"status": "error", "message": str(e)}

    @staticmethod
    async def revoke_agent_ownership(
        user_id: str, 
        agent_id: str, 
        revoked_by: str, 
        db: AsyncSession,
        reason: Optional[str] = None
    ) -> dict:
        """Revoke agent ownership from a user"""
        try:
            result = await db.execute(
                select(AgentOwnership).where(
                    and_(
                        AgentOwnership.user_id == user_id,
                        AgentOwnership.agent_id == agent_id
                    )
                )
            )
            ownership = result.scalar_one_or_none()
            
            if not ownership:
                return {"status": "error", "message": "Ownership record not found"}
            
            await db.delete(ownership)
            await db.commit()
            
            return {
                "status": "success",
                "message": f"Ownership revoked{f': {reason}' if reason else ''}",
                "user_id": user_id,
                "agent_id": agent_id
            }
        except Exception as e:
            await db.rollback()
            return {"status": "error", "message": str(e)}

    @staticmethod
    async def get_user_agent_stats(user_id: str, db: AsyncSession) -> dict:
        """Get statistics about a user's agent requests and ownership"""
        # Get owned agents count
        owned_result = await db.execute(
            select(AgentOwnership).where(AgentOwnership.user_id == user_id)
        )
        owned_count = len(owned_result.scalars().all())
        
        # Get request counts by status - Use scalar queries for counts
        pending_result = await db.execute(
            select(AgentRequest).where(
                and_(
                    AgentRequest.user_id == user_id,
                    AgentRequest.status == RequestStatus.PENDING.value
                )
            )
        )
        pending_count = len(pending_result.scalars().all())
        
        approved_result = await db.execute(
            select(AgentRequest).where(
                and_(
                    AgentRequest.user_id == user_id,
                    AgentRequest.status == RequestStatus.APPROVED.value
                )
            )
        )
        approved_count = len(approved_result.scalars().all())
        
        rejected_result = await db.execute(
            select(AgentRequest).where(
                and_(
                    AgentRequest.user_id == user_id,
                    AgentRequest.status == RequestStatus.REJECTED.value
                )
            )
        )
        rejected_count = len(rejected_result.scalars().all())
        
        # Get total requests count
        total_result = await db.execute(
            select(AgentRequest).where(AgentRequest.user_id == user_id)
        )
        total_count = len(total_result.scalars().all())
        
        return {
            "user_id": user_id,
            "owned_agents": owned_count,
            "pending_requests": pending_count,
            "approved_requests": approved_count,
            "rejected_requests": rejected_count,
            "total_requests": total_count
        }

    @staticmethod
    async def user_owns_agent(user_id: str, agent_id: str, db: AsyncSession) -> bool:
        """Check if a user owns a specific agent"""
        result = await db.execute(
            select(AgentOwnership).where(
                and_(
                    AgentOwnership.user_id == user_id,
                    AgentOwnership.agent_id == agent_id
                )
            )
        )
        ownership = result.scalar_one_or_none()
        return ownership is not None