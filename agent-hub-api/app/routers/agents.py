from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, Form
from fastapi import File as FastAPIFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict
import traceback
import time
from sqlalchemy import select

from app.database.connection import get_db_session
from app.services.chat_service import ChatService
from app.auth.dependencies import get_current_user
from app.models.schemas import QueryResponse
from app.database.models import User, UserRole, File, Query
from app.models.chat import ChatRequest, ChatResponse
from app.models.schemas import QueryResponse
from app.agent_loader import load_agents, build_dynamic_agent
from app.utils.pdf_processor import PDFProcessor
from app.services.agent_sync_service import AgentSyncService
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.callbacks import TokenCountingHandler
from app.config import LLM_MAX_ITERATIONS
from app.utils.logging import setup_logging
from app.services.file_service import FileService
from app.models.file import FileCreate
from app.utils.circuit_breaker import (
    circuit_breaker_manager, 
    CircuitBreakerConfig, 
    CircuitBreakerOpenError, 
    CircuitBreakerTimeoutError,
    RateLimitError
)
from app.utils.activity_logger import ActivityLogger
from app.utils.agent_optimizer import get_agent_recommendations
from app.utils.demo_simulator import create_demo_response_for_query
from app.utils.speed_optimizer import speed_optimizer

logger = setup_logging(__name__)
router = APIRouter(prefix="/agents", tags=["Agents"])
chat_service = ChatService()
file_service = FileService()


@router.post("/query", response_model=ChatResponse)
async def query_agent(
    request: Request, 
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Query agent with user authentication and chat history."""
    agents: Dict[str, ReActAgent] = getattr(request.app.state, "agent", {})

    if not agents:
        raise HTTPException(status_code=503, detail="No agents loaded")

    # Select the requested agent or default
    agent_name: Optional[str] = payload.agent_name
    if agent_name not in agents:
        agent_name = next(iter(agents.keys()))
        logger.warning(f"⚠️ Requested agent '{payload.agent_name}' not found, using '{agent_name}'")

    # Fix: Check if user has access to this agent (owns it or is admin)
    is_admin = bool(getattr(current_user, "role", None) == UserRole.ADMIN)  # Convert to Python bool
    if not is_admin:
        # Find the agent in the database by name
        db_agent = await AgentSyncService.get_agent_by_name(db, agent_name)
        if db_agent:
            agent_id = db_agent["id"]
            # Fix: Convert current_user.id to string to avoid SQLAlchemy type issues
            user_id = str(getattr(current_user, 'id', ''))
            owns_agent = await AgentSyncService.user_owns_agent(user_id, agent_id, db)
            if not owns_agent:
                raise HTTPException(status_code=403, detail=f"Access denied to agent '{agent_name}'")
        else:
            # If agent doesn't exist in DB but exists in memory, it might be a system agent
            # In this case, we might want to allow access or deny based on policy
            # For now, we'll allow it to maintain backward compatibility
            pass

    agent = agents[agent_name]

    try:
        # Fix: Safe access to username
        username = getattr(current_user, 'username', 'unknown')
        logger.info(f"🤖 Using agent: {agent_name} for user: {username}")
        
        # Check for persisted PDF context
        pdf_context = await file_service.get_latest_pdf_context(db, str(current_user.id))
        enhanced_prompt = payload.prompt
        
        if pdf_context:
            # Create a simple PDF data structure for the context creator
            pdf_data = {
                "content": pdf_context.content,
                "summary": pdf_context.summary or "Previous PDF context"
            }
            enhanced_prompt = PDFProcessor.create_pdf_context(pdf_data, payload.prompt)
            logger.info(f"📎 Using persisted PDF context for user: {username}")

        # Run the agent with circuit breaker protection
        circuit_breaker = circuit_breaker_manager.get_breaker(
            f"agent_{agent_name}",
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=60.0,
                timeout=120.0  # 2 minute timeout for single agent
            )
        )
        
        async def run_agent():
            return await agent.run(enhanced_prompt, max_iterations=LLM_MAX_ITERATIONS)
        
        try:
            result = await circuit_breaker.call(run_agent)
        except CircuitBreakerOpenError:
            raise HTTPException(
                status_code=503,
                detail=f"Agent '{agent_name}' is temporarily unavailable due to repeated failures"
            )
        except CircuitBreakerTimeoutError:
            raise HTTPException(
                status_code=408,
                detail=f"Agent '{agent_name}' execution timed out - try a simpler query"
            )

        # Token usage
        handler = next(
            (h for h in getattr(agent.llm.callback_manager, "handlers", [])
             if isinstance(h, TokenCountingHandler)),
            None,
        )

        token_usage = {}
        if handler:
            token_usage = {
                "total_tokens": getattr(handler, "total_llm_token_count", 0),
                "prompt_tokens": getattr(handler, "prompt_llm_token_count", 0),
                "completion_tokens": getattr(handler, "completion_llm_token_count", 0),
            }
            logger.info(f"🧾 Token Usage: {token_usage}")

        # Log agent usage event
        activity_logger = ActivityLogger(db)
        await activity_logger.log_agent_event(
            f"Agent '{agent_name}' processed query for user ID {current_user.id}",
            user_id=str(current_user.id),
            metadata={
                "agent_name": agent_name,
                "prompt_length": len(payload.prompt),
                "token_usage": token_usage,
                "has_pdf_context": pdf_context is not None
            }
        )

        return ChatResponse(
            response=str(result),
            token_usage=token_usage,
            agent_used=agent_name,
        )
    except Exception as e:
        logger.exception(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Agent failed to process query: {e}")


@router.post("/multi-agent-query", response_model=QueryResponse)
async def multi_agent_query(
    request: Request,
    prompt: str = Form(..., description="User query/prompt"),
    agent_name: Optional[str] = Form(None, description="Comma-separated agent names"),
    chat_id: Optional[str] = Form(None, description="Chat ID to add this query to"),
    files: List[UploadFile] = FastAPIFile(default=[], description="PDF files to upload and analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Multi-agent query with authentication, chat history, and PDF upload support."""
    agents: Dict[str, ReActAgent] = getattr(request.app.state, "agent", {})

    if not agents:
        raise HTTPException(status_code=503, detail="No agents loaded")

    # Parse and optimize agent names
    agent_name_str = agent_name or ""
    requested_agents = [name.strip() for name in agent_name_str.split(",") if name.strip()]
    
    # Use agent optimizer for better selection
    optimization_result = get_agent_recommendations(requested_agents, agents)
    agent_names = optimization_result['agents']
    
    # Log optimization results
    if optimization_result['warnings']:
        for warning in optimization_result['warnings']:
            logger.warning(f"⚠️ Agent selection: {warning}")
    
    if optimization_result['recommendations']:
        for rec in optimization_result['recommendations']:
            logger.info(f"💡 Recommendation: {rec}")
    
    logger.info(f"🎯 Agent selection: {optimization_result['original_count']} → {optimization_result['optimized_count']} agents")
    
    # If no agents after optimization, use default
    if not agent_names:
        default_agent = next(iter(agents.keys())) if agents else None
        if default_agent:
            agent_names = [default_agent]
            logger.info(f"No agents after optimization, using default: {default_agent}")
        else:
            logger.error("No agents available")
            raise HTTPException(status_code=503, detail="No agents available")

    # Fix: Check if user has access to all requested agents (owns them or is admin)
    is_admin = bool(getattr(current_user, "role", None) == UserRole.ADMIN)  # Convert to Python bool
    if not is_admin:
        # Fix: Convert current_user.id to string to avoid SQLAlchemy type issues
        user_id = str(getattr(current_user, 'id', ''))
        
        # Check access for each requested agent
        for agent_name in agent_names:
            if agent_name not in agents:
                raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
            
            # Find the agent in the database by name
            db_agent = await AgentSyncService.get_agent_by_name(db, agent_name)
            if db_agent:
                agent_id = db_agent["id"]
                owns_agent = await AgentSyncService.user_owns_agent(user_id, agent_id, db)
                if not owns_agent:
                    raise HTTPException(status_code=403, detail=f"Access denied to agent '{agent_name}'")
            else:
                # If agent doesn't exist in DB but exists in memory, it might be a system agent
                # In this case, we might want to allow access or deny based on policy
                # For now, we'll allow it to maintain backward compatibility
                pass

    # Fix: Convert current_user.id to string for all database operations
    user_id = str(getattr(current_user, 'id', ''))
    
    # Process uploaded files first to save them to the database
    file_records = []
    if files:
        for uploaded_file in files:
            if uploaded_file.filename:
                # Read file content
                content = await uploaded_file.read()
                await uploaded_file.seek(0)  # Reset file pointer for PDF processing
                
                file_create = FileCreate(
                    name=uploaded_file.filename,
                    content_type=uploaded_file.content_type or "application/pdf",
                    size=len(content),
                )
                
                # Save file to database and disk
                file_record = await file_service.create_file(
                    db, file_create, user_id, content
                )
                # Attach file_id to the uploaded file for context saving
                uploaded_file.file_id = file_record.id
                file_records.append(file_record)
    
    if chat_id:
        # Add to existing chat
        from app.models.schemas import QueryRequest
        query_data = QueryRequest(
            message=prompt,
            # Fix: Safe filename extraction to avoid SQLAlchemy type issues
            files=[str(getattr(file, 'filename', '')) for file in files if getattr(file, 'filename', None)],
            selected_agents=agent_names
        )
        query_obj = await chat_service.add_query_to_chat(db, chat_id, user_id, query_data)
        if not query_obj:
            raise HTTPException(status_code=404, detail="Chat not found")
    else:
        # Create new chat
        from app.models.schemas import ChatCreate
        chat_data = ChatCreate(
            message=prompt,
            # Fix: Safe filename extraction to avoid SQLAlchemy type issues
            files=[str(getattr(file, 'filename', '')) for file in files if getattr(file, 'filename', None)],
            selected_agents=agent_names
        )
        chat = await chat_service.create_chat(db, current_user, chat_data)
        
        # Fix: Better approach to get the query from the new chat
        if chat:
            # Convert chat.id to string to avoid SQLAlchemy type issues
            chat_id_str = str(getattr(chat, 'id', ''))
            try:
                chat_with_queries = await chat_service.get_chat(db, chat_id_str, user_id)
                # Fix: Safe access to queries attribute
                queries = getattr(chat_with_queries, 'queries', []) if chat_with_queries else []
                query_obj = queries[0] if queries else None
            except Exception as e:
                logger.warning(f"Failed to get chat with queries: {e}")
                # If we can't get the chat with queries, we'll create a simple query object
                # This is a fallback - you might want to handle this differently
                query_obj = None

    if not query_obj:
        raise HTTPException(status_code=500, detail="Failed to create query")

    # Associate files with the query and chat
    if file_records and query_obj:
        query_id = str(getattr(query_obj, 'id', ''))
        # Get the chat_id from the query object
        query_chat_id = str(getattr(query_obj, 'chat_id', ''))
        
        for file_record in file_records:
            file_record.query_id = query_id
            file_record.chat_id = query_chat_id
        await db.commit()
        
        # Update the query with detailed file metadata including file IDs
        result = await db.execute(select(Query).where(Query.id == query_id))
        query = result.scalar_one_or_none()
        if query:
            query.files_uploaded = chat_service._process_file_records_metadata(file_records)
            await db.commit()
            await db.refresh(query)

    try:
        # Fix: Convert query_obj.id to string to avoid SQLAlchemy type issues
        query_id = str(getattr(query_obj, 'id', ''))
        
        # Update query status to processing
        await chat_service.update_query_response(
            db, 
            query_id,  # Use converted string ID
            response="", 
            status="processing"
        )

        # Process uploaded PDF files (just for content extraction, not storage)
        pdf_data = await PDFProcessor.process_pdfs(files, db, user_id)
        has_pdf_context = bool(pdf_data.get("content"))
        pdf_summary = pdf_data.get("summary") if has_pdf_context else None

        # Get conversation history for context if this is an existing chat
        conversation_context = ""
        if chat_id:
            try:
                # Get the chat with all queries for context
                chat_with_history = await chat_service.get_chat(db, chat_id, user_id)
                if chat_with_history:
                    # Fix: Safe access to queries attribute
                    history_queries = getattr(chat_with_history, 'queries', [])
                    if history_queries:
                        # Build conversation context from previous queries (excluding the current one)
                        context_parts = []
                        for q in history_queries[:-1]:  # Exclude the last query (current one)
                            q_message = getattr(q, 'message', None)
                            q_response = getattr(q, 'response', None)
                            if q_message and q_response:
                                context_parts.append(f"Human: {q_message}")
                                context_parts.append(f"Assistant: {q_response}")
                        
                        if context_parts:
                            conversation_context = "\n\nPrevious conversation:\n" + "\n".join(context_parts) + "\n\nCurrent question:\n"
                            logger.info(f"💬 Added conversation context with {len(context_parts)//2} previous exchanges")
                        
            except Exception as e:
                logger.warning(f"Failed to get conversation history: {e}")
                conversation_context = ""

        # Create enhanced prompt with conversation context and PDF context
        enhanced_prompt = PDFProcessor.create_pdf_context(pdf_data, conversation_context + prompt)

        # Log PDF processing results
        # Fix: Safe access to username
        username = getattr(current_user, 'username', 'unknown')
        if files:
            logger.info(f"📄 Processed {len(files)} PDF files for user {username}")
            for file_info in pdf_data.get("files", []):
                if file_info.get("processed"):
                    logger.info(f"  ✅ {file_info['name']}: {file_info['pages']} pages")
                else:
                    logger.warning(f"  ❌ {file_info['name']}: {file_info.get('error', 'Unknown error')}")

        # Build dynamic agent (GitHub tokens are handled during agent loading)
        temp_agent = await build_dynamic_agent(
            agent_names,  # Use original agent selection
            agents,
            has_pdf_context=has_pdf_context,
            pdf_summary=pdf_summary,
        )

        logger.info(f"🎯 Optimized agent selection: {agent_names} (from original: {agent_name_str})")
        if has_pdf_context:
            logger.info(f"📄 Agent configured with PDF context: {pdf_summary}")

        # Run dynamic agent with circuit breaker protection
        # Adjust timeout based on number of agents
        base_timeout = 120.0  # 2 minutes base
        timeout_per_agent = 60.0  # 1 minute per additional agent
        total_timeout = base_timeout + (len(agent_names) - 1) * timeout_per_agent
        total_timeout = min(total_timeout, 480.0)  # Cap at 8 minutes
        
        circuit_breaker = circuit_breaker_manager.get_breaker(
            f"multi_agent_{'_'.join(sorted(agent_names))}",  # Sort for consistent naming
            CircuitBreakerConfig(
                failure_threshold=2,  # Lower threshold for multi-agent
                recovery_timeout=120.0,
                timeout=total_timeout
            )
        )
        
        logger.info(f"🤖 Running {len(agent_names)} agents with {total_timeout:.0f}s timeout: {agent_names}")
        
        async def run_multi_agent():
            return await temp_agent.run(enhanced_prompt, max_iterations=LLM_MAX_ITERATIONS)
        
        try:
            result = await circuit_breaker.call(run_multi_agent)
        except CircuitBreakerOpenError as e:
            logger.warning(f"⚡ Circuit breaker open: {e}")
            # Update query with circuit breaker error
            if 'query_id' in locals() and query_id:
                await chat_service.update_query_error(db, query_id, error_message=str(e))
            raise HTTPException(
                status_code=503,
                detail=f"Multi-agent system ({', '.join(agent_names)}) is temporarily unavailable"
            )
        except CircuitBreakerTimeoutError as e:
            logger.warning(f"⏰ Multi-agent timeout: {e}")
            # Update query with timeout error  
            if 'query_id' in locals() and query_id:
                await chat_service.update_query_error(db, query_id, error_message="Execution timed out")
            raise HTTPException(
                status_code=408,
                detail="Multi-agent execution timed out - try with fewer agents or a simpler query"
            )
        except RateLimitError as e:
            logger.warning(f"⚠️ Rate limit hit: {e}")
            
            # Provide demo response for common demo queries
            demo_response = create_demo_response_for_query(prompt)
            
            # Update query with demo response
            if 'query_id' in locals() and query_id:
                updated_query = await chat_service.update_query_response(
                    db,
                    query_id,
                    response=demo_response,
                    agent_used=f"Demo Mode ({', '.join(agent_names)})",
                    status="completed"
                )
                return QueryResponse.from_orm(updated_query)
            
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded - please wait 60 seconds before trying again"
            )

        # Token usage logging
        handler = next(
            (h for h in getattr(temp_agent.llm.callback_manager, "handlers", [])
             if isinstance(h, TokenCountingHandler)),
            None,
        )
        token_usage = {
            "total_tokens": getattr(handler, "total_llm_token_count", 0),
            "prompt_tokens": getattr(handler, "prompt_llm_token_count", 0),
            "completion_tokens": getattr(handler, "completion_llm_token_count", 0),
        } if handler else {}

        # Log agent usage event
        activity_logger = ActivityLogger(db)
        await activity_logger.log_agent_event(
            f"Multi-agent query processed: {', '.join(agent_names)}",
            user_id=str(current_user.id),
            metadata={
                "agents_used": agent_names,
                "prompt_length": len(prompt),
                "file_count": len(files),
                "token_usage": token_usage,
                "has_pdf_context": has_pdf_context
            }
        )

        # Update query with response (use the same converted ID)
        updated_query = await chat_service.update_query_response(
            db,
            query_id,  # Use converted string ID
            response=str(result),
            agent_used=", ".join(agent_names),
            token_usage=token_usage,
            status="completed"
        )

        return QueryResponse.from_orm(updated_query)

    except Exception as e:
        # Fix: Safe access to username in exception handler
        username = getattr(current_user, 'username', 'unknown')
        logger.exception(f"Agent failed for user {username}: {traceback.format_exc()}")
        
        # Update query with error (use the same converted ID)
        query_id = str(getattr(query_obj, 'id', '')) if query_obj else ''
        if query_id:
            await chat_service.update_query_error(
                db,
                query_id,  # Use converted string ID
                error_message=str(e)
            )
        
        # Check for GitHub-specific errors
        if "401" in str(e) and "github" in str(e).lower():
            raise HTTPException(
                status_code=401, 
                detail="GitHub authentication required. Please reconnect your GitHub account."
            )
        elif "403" in str(e) and "github" in str(e).lower():
            raise HTTPException(
                status_code=403,
                detail="GitHub token lacks required permissions. Please reconnect your GitHub account."
            )
        elif "502" in str(e) or "Bad Gateway" in str(e):
            raise HTTPException(
                status_code=413,
                detail="Request too large. Try with smaller PDF files or more specific queries."
            )
        
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)[:200]}")


@router.post("/scan-github-security", response_model=QueryResponse)
async def scan_github_security(
    request: Request,
    github_url: str = Form(..., description="GitHub repository URL to scan"),
    chat_id: Optional[str] = Form(None, description="Chat ID to add this query to"),
    severity_threshold: str = Form("low", description="Minimum severity level: low, medium, high, critical"),
    include_dev_deps: bool = Form(True, description="Include development dependencies in scan"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Specialized endpoint for GitHub repository security scanning with Snyk.
    
    This endpoint provides the specific workflow:
    1. User provides GitHub repository URL
    2. System clones the repository
    3. Runs Snyk vulnerability scan
    4. Returns combined report with repository info and vulnerabilities
    """
    agents: Dict[str, ReActAgent] = getattr(request.app.state, "agent", {})

    # Use the GitHub + Snyk combined agent
    agent_name = "github_security_agent"
    
    if agent_name not in agents:
        # Fallback to separate agents if combined agent not available
        if "github_agent" in agents and "snyk_scanner_agent" in agents:
            agent_name = "snyk_scanner_agent"  # Use Snyk agent for scanning
        else:
            raise HTTPException(
                status_code=503, 
                detail="GitHub security scanning agents not available"
            )

    # Check user access to the agent
    is_admin = bool(getattr(current_user, "role", None) == UserRole.ADMIN)
    if not is_admin:
        user_id = str(getattr(current_user, 'id', ''))
        db_agent = await AgentSyncService.get_agent_by_name(db, agent_name)
        if db_agent:
            agent_id = db_agent["id"]
            owns_agent = await AgentSyncService.user_owns_agent(user_id, agent_id, db)
            if not owns_agent:
                raise HTTPException(status_code=403, detail=f"Access denied to agent '{agent_name}'")

    agent = agents[agent_name]

    try:
        user_id = str(getattr(current_user, 'id', ''))
        username = getattr(current_user, 'username', 'unknown')
        
        # Create a specialized prompt for GitHub security scanning
        scan_prompt = f"""
        Please perform a comprehensive security scan of the GitHub repository: {github_url}
        
        Follow this workflow:
        1. Clone the repository from the provided GitHub URL
        2. Run Snyk vulnerability scanning with the following parameters:
           - Severity threshold: {severity_threshold}
           - Include dev dependencies: {include_dev_deps}
        3. Analyze the results and provide:
           - Total vulnerability count by severity
           - Most critical vulnerabilities (top 10)
           - Affected packages and versions
           - Remediation recommendations
           - Risk assessment
        4. Format the response as a comprehensive security report
        
        Repository URL: {github_url}
        Severity threshold: {severity_threshold}
        Include dev dependencies: {"yes" if include_dev_deps else "no"}
        """

        # Create a query record in the database
        query_data = {
            "message": f"Security scan of {github_url}",
            "response": "",
            "agent_used": agent_name,
            "status": "processing",
            "metadata": {
                "scan_type": "github_security",
                "repository_url": github_url,
                "severity_threshold": severity_threshold,
                "include_dev_deps": include_dev_deps
            }
        }

        query_obj = await chat_service.create_query(
            db=db,
            query_data=query_data,
            user_id=user_id,
            chat_id=chat_id
        )

        if not query_obj:
            raise HTTPException(status_code=500, detail="Failed to create query")

        query_id = str(getattr(query_obj, 'id', ''))

        logger.info(f"🔍 Starting GitHub security scan for {github_url} by user {username}")
        
        # Run the security scanning agent with circuit breaker protection
        circuit_breaker = circuit_breaker_manager.get_breaker(
            "github_security_scan",
            CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout=180.0,
                timeout=600.0  # 10 minute timeout for security scans
            )
        )
        
        async def run_security_scan():
            return await agent.run(scan_prompt, max_iterations=LLM_MAX_ITERATIONS)
        
        try:
            result = await circuit_breaker.call(run_security_scan)
        except CircuitBreakerOpenError:
            raise HTTPException(
                status_code=503,
                detail="GitHub security scanning is temporarily unavailable due to repeated failures"
            )
        except CircuitBreakerTimeoutError:
            raise HTTPException(
                status_code=408,
                detail="Security scan timed out - the repository may be too large or complex"
            )

        # Token usage logging
        handler = next(
            (h for h in getattr(agent.llm.callback_manager, "handlers", [])
             if isinstance(h, TokenCountingHandler)),
            None,
        )
        token_usage = {
            "total_tokens": getattr(handler, "total_llm_token_count", 0),
            "prompt_tokens": getattr(handler, "prompt_llm_token_count", 0),
            "completion_tokens": getattr(handler, "completion_llm_token_count", 0),
        } if handler else {}

        # Log security scan event
        activity_logger = ActivityLogger(db)
        await activity_logger.log_agent_event(
            f"GitHub security scan completed: {github_url}",
            user_id=user_id,
            metadata={
                "agent_used": agent_name,
                "repository_url": github_url,
                "severity_threshold": severity_threshold,
                "include_dev_deps": include_dev_deps,
                "token_usage": token_usage
            }
        )

        # Update query with results
        updated_query = await chat_service.update_query_response(
            db,
            query_id,
            response=str(result),
            agent_used=agent_name,
            token_usage=token_usage,
            status="completed"
        )

        logger.info(f"✅ GitHub security scan completed for {github_url}")

        return QueryResponse.from_orm(updated_query)

    except Exception as e:
        logger.exception(f"GitHub security scan failed for {github_url}: {traceback.format_exc()}")
        
        # Update query with error if query was created
        if 'query_id' in locals() and query_id:
            await chat_service.update_query_error(
                db,
                query_id,
                error_message=str(e)
            )
        
        # Handle specific error types
        if "github" in str(e).lower() and ("401" in str(e) or "authentication" in str(e).lower()):
            raise HTTPException(
                status_code=401,
                detail="GitHub authentication required. Please ensure GitHub token is configured."
            )
        elif "snyk" in str(e).lower() and ("401" in str(e) or "authentication" in str(e).lower()):
            raise HTTPException(
                status_code=401,
                detail="Snyk authentication required. Please ensure Snyk is configured and authenticated."
            )
        elif "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=404,
                detail=f"Repository not found or not accessible: {github_url}"
            )
        
        raise HTTPException(status_code=500, detail=f"Security scan failed: {str(e)[:200]}")


@router.get("/health")
async def get_agent_health(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get health status of all agents and circuit breakers."""
    agents: Dict[str, ReActAgent] = getattr(request.app.state, "agent", {})
    
    # Get circuit breaker stats
    circuit_stats = circuit_breaker_manager.get_all_stats()
    
    # Basic agent status
    agent_status = {}
    for name, agent in agents.items():
        try:
            # Test if agent has tools
            tool_count = len(getattr(agent, "tools", []))
            agent_status[name] = {
                "status": "healthy" if tool_count > 0 else "degraded",
                "tool_count": tool_count,
                "has_llm": hasattr(agent, "llm") and agent.llm is not None
            }
        except Exception as e:
            agent_status[name] = {
                "status": "unhealthy",
                "error": str(e),
                "tool_count": 0,
                "has_llm": False
            }
    
    return {
        "timestamp": time.time(),
        "agents": agent_status,
        "circuit_breakers": circuit_stats,
        "total_agents": len(agents),
        "healthy_agents": sum(1 for status in agent_status.values() if status["status"] == "healthy"),
        "max_iterations": LLM_MAX_ITERATIONS
    }


@router.get("/available")
async def list_available_agents(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List all available agents for the authenticated user."""
    agents: Dict[str, ReActAgent] = getattr(request.app.state, "agent", {})
    
    # Fix: Filter agents based on user access
    is_admin = bool(getattr(current_user, "role", None) == UserRole.ADMIN)  # Convert to Python bool
    if is_admin:
        # Admins can see all agents
        accessible_agent_names = set(agents.keys())
    else:
        # Regular users can only see agents they own
        # Fix: Convert current_user.id to string to avoid SQLAlchemy type issues
        user_id = str(getattr(current_user, 'id', ''))
        owned_agents = await AgentSyncService.get_owned_agents(user_id, db)
        accessible_agent_names = {agent["name"] for agent in owned_agents}
    
    result: Dict[str, List[str]] = {}
    
    for name, agent in agents.items():
        # Only include agents the user has access to
        if name in accessible_agent_names:
            tool_names: List[str] = []
            for tool in getattr(agent, "tools", []):
                md = getattr(tool, "metadata", None)
                tool_names.append(getattr(md, "name", "unknown"))
            result[name] = tool_names
    
    # Fix: Safe access to current_user attributes
    github_connected = bool(getattr(current_user, "github_token", None))
    username = getattr(current_user, 'username', 'unknown')
    
    # Check if user has any persisted PDF context
    pdf_contexts = await file_service.get_user_pdf_contexts(db, str(current_user.id))
    has_pdf_context = len(pdf_contexts) > 0
    
    return {
        "available_agents": result,
        "user": username,
        "github_connected": github_connected,
        "has_pdf_context": has_pdf_context
    }