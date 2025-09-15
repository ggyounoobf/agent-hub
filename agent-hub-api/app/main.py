from fastapi import FastAPI, HTTPException, Request, UploadFile, Form
from fastapi import File as FastAPIFile
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Optional, List, Any
import traceback
import os
import re

from app.models import ChatRequest, ChatResponse
from app.agent_loader import load_agents, build_dynamic_agent
from app.utils.pdf_processor import PDFProcessor
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.callbacks import TokenCountingHandler
from app.config import LLM_MAX_ITERATIONS
from app.utils.logging import setup_logging

# Import routers
from app.routers import auth, chat, agents, admin, marketplace, files, analytics

# Import database initialization
from app.database.init_db import create_tables, create_default_admin_user
from app.database.populate_db import populate_database

# Database imports for optional chat saving
from app.database.connection import get_db_session  
from app.services.chat_service import ChatService
from app.services.agent_sync_service import AgentSyncService
from app.models.schemas import ChatCreate
from sqlalchemy.ext.asyncio import AsyncSession

# Import User model and dependencies for authentication
from app.database.models import User, UserRole
from app.auth.dependencies import get_current_user
from fastapi import Depends

# Import AgentInfo type
from app.agents.agent_builders import AgentInfo
from app.config import (
    ALLOWED_ORIGINS
)

# Import file service and models
from app.services.file_service import FileService
from app.models.file import FileCreate

logger = setup_logging(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # 🚀 Startup logic
    try:
        logger.info("🔧 Initializing database...")
        await create_tables()
        await create_default_admin_user()
        await populate_database()
        logger.info("✅ Database initialization complete.")
        
        logger.info(f"🔄 Max iterations: {LLM_MAX_ITERATIONS}")
        logger.info("🔧 Initializing ReActAgent(s) with MCP tools...")

        # Optional: preload GitHub hosted MCP tools (PAT or OAuth access token) from env
        startup_github_token = os.environ.get("GITHUB_TOKEN")

        db_gen = get_db_session()
        db = await db_gen.__anext__()
        try:
            agents = await load_agents(db, github_token=startup_github_token)
            await AgentSyncService.sync_agents_to_db(agents, db)
        finally:
            await db_gen.aclose()

        logger.info("✅ Agent DB sync complete.")

        app.state.agent = agents
        logger.info("✅ Agent setup complete.")
    except Exception:
        logger.exception("❌ Startup failed")
        app.state.agent = None

    yield  # FastAPI is now serving

    # ✅ App is serving
    if app.state.agent:
        logger.info("🚀 MCP OpenAI Client API is up and agents are loaded.")
    else:
        logger.info("🚀 MCP OpenAI Client API is up but agents failed to load.")

    # 🧹 Shutdown logic
    try:
        agents_obj = getattr(app.state, "agent", None)
        if agents_obj:
            logger.info("🛑 Cleaning up agents...")
            app.state.agent = None
            logger.info("✅ Agent cleanup complete.")
    except Exception:
        logger.exception("⚠️ Agent shutdown failed")

app = FastAPI(
    title="Agent Hub API",
    description="This API provides authentication, chat management, and MCP agent integration with OpenAI backend.",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(agents.router)
app.include_router(admin.router)
app.include_router(marketplace.router)
app.include_router(files.router)
app.include_router(analytics.router)

def _extract_github_token(req: Request) -> Optional[str]:
    """
    Prefer per-request token (Authorization: Bearer <token> or X-GitHub-Token),
    fall back to env var GITHUB_TOKEN.
    """
    auth = (req.headers.get("authorization") or "").strip()
    m = re.match(r"(?i)^bearer\s+(.+)$", auth)
    if m:
        return m.group(1).strip()
    hdr = req.headers.get("x-github-token")
    if hdr:
        return hdr.strip()
    return os.environ.get("GITHUB_TOKEN")

@app.get("/healthz", tags=["System"])
async def health_check(request: Request):
    agent_loaded = getattr(request.app.state, "agent", None) is not None
    return {
        "status": "ok" if agent_loaded else "initializing",
        "agent_loaded": agent_loaded,
    }

@app.get("/agents", tags=["System"])
async def list_agents(request: Request):
    """List all available agents in the system (internal use only)"""
    agents: Dict[str, AgentInfo] = getattr(request.app.state, "agent", {})  # Fixed type
    result: Dict[str, Any] = {}
    
    for name, agent_info in agents.items():
        tool_names: List[str] = []
        for tool in agent_info.tools:
            md = getattr(tool, "metadata", None)
            tool_names.append(getattr(md, "name", "unknown"))
        
        result[name] = {
            "description": agent_info.description,
            "tools": tool_names
        }
    
    return {"available_agents": result}

@app.post("/query", response_model=ChatResponse, tags=["Query"])
async def query_agent(request: Request, payload: ChatRequest, current_user: User = Depends(get_current_user)):
    agents: Dict[str, AgentInfo] = getattr(request.app.state, "agent", {})  # Fixed type

    if not agents:
        raise HTTPException(status_code=503, detail="No agents loaded")

    # Select the requested agent or default
    agent_name: Optional[str] = payload.agent_name
    if agent_name not in agents:
        # Fall back to first available agent
        agent_name = next(iter(agents.keys()))
        logger.warning(f"⚠️ Requested agent '{payload.agent_name}' not found, using '{agent_name}'")

    agent = agents[agent_name].agent  # Access the ReActAgent inside AgentInfo

    try:
        logger.info(f"🤖 Using agent: {agent_name}")
        # Run the agent
        result = await agent.run(payload.prompt, max_iterations=LLM_MAX_ITERATIONS)

        # 🧾 Token usage
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

        return ChatResponse(
            response=str(result),
            token_usage=token_usage,
            agent_used=agent_name,
        )
    except Exception as e:
        logger.exception(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Agent failed to process query: {e}")

@app.post("/multi-agent-query", response_model=ChatResponse, tags=["Query"])
async def multi_agent_query(
    request: Request,
    prompt: str = Form(..., description="User query/prompt"),
    agent_name: Optional[str] = Form(None, description="Comma-separated agent names (e.g., 'sample_agent,github_agent')"),
    files: List[UploadFile] = FastAPIFile(default=[], description="PDF files to upload and analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Multi-agent query endpoint with PDF upload support.

    - prompt: Your question or instruction
    - agent_name: Comma-separated list of agents (e.g., "sample_agent,github_agent")
    - files: PDF files to upload for analysis (multipart/form-data)
    """
    agents: Dict[str, AgentInfo] = getattr(request.app.state, "agent", {})

    if not agents:
        raise HTTPException(status_code=503, detail="No agents loaded")

    # Parse agent names
    agent_name_str = agent_name or ""
    agent_names = [name.strip() for name in agent_name_str.split(",") if name.strip()]

    try:
        # Read file contents first
        file_contents = []
        for uploaded_file in files:
            if uploaded_file.filename:
                content = await uploaded_file.read()
                file_contents.append((uploaded_file, content))
                # Reset file pointer for PDF processing
                await uploaded_file.seek(0)
        
        # 📄 Process uploaded PDF files
        pdf_data = await PDFProcessor.process_pdfs(files)
        
        # Save files to database if any were uploaded
        file_records = []
        if files:
            file_service = FileService()
            for i, (uploaded_file, content) in enumerate(file_contents):
                if uploaded_file.filename:
                    file_create = FileCreate(
                        name=uploaded_file.filename,
                        content_type=uploaded_file.content_type or "application/pdf",
                        size=len(content),
                        # chat_id and query_id will be set when we have them
                    )
                    
                    # Save file
                    file_record = await file_service.create_file(
                        db, file_create, current_user.id, content
                    )
                    
                    file_records.append(file_record)

        # Check if we have PDF content
        has_pdf_context = bool(pdf_data.get("content"))
        pdf_summary = pdf_data.get("summary") if has_pdf_context else None

        # 🔧 Create enhanced prompt with PDF context
        enhanced_prompt = PDFProcessor.create_pdf_context(pdf_data, prompt)

        # Log PDF processing results
        if files:
            logger.info(f"📄 Processed {len(files)} PDF files: {pdf_data.get('summary')}")
            for file_info in pdf_data.get("files", []):
                if file_info.get("processed"):
                    logger.info(f"  ✅ {file_info['name']}: {file_info['pages']} pages, {file_info['word_count']} words")
                else:
                    logger.warning(f"  ❌ {file_info['name']}: {file_info.get('error', 'Unknown error')}")

        # Extract just the ReActAgent objects for build_dynamic_agent
        react_agents = {name: info.agent for name, info in agents.items()}

        temp_agent = await build_dynamic_agent(
            agent_names,
            react_agents,  # Pass extracted agents
            has_pdf_context=has_pdf_context,
            pdf_summary=pdf_summary
        )

        logger.info(f"🤖 Running dynamic agent composed of: {agent_names}")
        if has_pdf_context:
            logger.info(f"📄 Agent configured with PDF context: {pdf_summary}")

        result = await temp_agent.run(enhanced_prompt, max_iterations=LLM_MAX_ITERATIONS)

        # 🧾 Token usage logging
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

        return ChatResponse(
            response=str(result),
            token_usage=token_usage,
            agent_used=", ".join(agent_names),
        )
    except Exception as e:
        logger.exception(traceback.format_exc())
        
        # Enhanced error handling
        if "context_length_exceeded" in str(e) or "maximum context length" in str(e):
            raise HTTPException(
                status_code=413,
                detail="Content exceeds model limits. Try with smaller PDF files, shorter prompts, or more specific queries."
            )
        elif "401" in str(e) and "github" in str(e).lower():
            raise HTTPException(
                status_code=401, 
                detail="GitHub authentication required."
            )
        elif "403" in str(e) and "github" in str(e).lower():
            raise HTTPException(
                status_code=403,
                detail="GitHub token lacks required permissions."
            )
        elif "502" in str(e) or "Bad Gateway" in str(e):
            raise HTTPException(
                status_code=413,
                detail="Request too large. Try with smaller files."
            )
        
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)[:200]}")

# Keep the original JSON endpoint for backward compatibility
@app.post("/multi-agent-query-json", response_model=ChatResponse, tags=["Query"])
async def multi_agent_query_json(
    request: Request, 
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Multi-agent query endpoint with optional database saving (JSON only, no file support)."""
    agents: Dict[str, AgentInfo] = getattr(request.app.state, "agent", {})

    if not agents:
        raise HTTPException(status_code=503, detail="No agents loaded")

    agent_name: Optional[str] = payload.agent_name
    agent_name_str = agent_name or ""
    agent_names = [name.strip() for name in agent_name_str.split(",") if name.strip()]

    try:
        # Extract just the ReActAgent objects for build_dynamic_agent
        react_agents = {name: info.agent for name, info in agents.items()}

        temp_agent = await build_dynamic_agent(agent_names, react_agents)

        logger.info(f"🤖 Running dynamic agent composed of: {agent_names}")
        result = await temp_agent.run(payload.prompt, max_iterations=LLM_MAX_ITERATIONS)

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

        response_text = str(result).strip() if result else "No response generated"

        # Try to save to database (without authentication for backward compatibility)
        try:
            chat_service = ChatService()
            
            # Create a simple user-like object for anonymous chats (you might want to create a system user)
            # For now, we'll create anonymous chats - you may want to modify this approach
            from app.database.models import User
            from sqlalchemy import select
            
            # Try to find or create an anonymous/system user for saving chats
            system_user_result = await db.execute(
                select(User).where(User.username == "anonymous")
            )
            system_user = system_user_result.scalar_one_or_none()
            
            if not system_user:
                # Create anonymous user for storing chats
                from uuid import uuid4
                system_user = User(
                    id=str(uuid4()),
                    username="anonymous",
                    email="anonymous@system.local",
                    full_name="Anonymous User",
                    provider="system"
                )
                db.add(system_user)
                await db.flush()
            
            # Create chat with the query and response
            chat_data = ChatCreate(
                message=payload.prompt,
                selected_agents=agent_names,
                title=payload.prompt[:50] + ("..." if len(payload.prompt) > 50 else "")
            )
            
            chat = await chat_service.create_chat(db, system_user, chat_data)
            
            # Update the first query with the response
            if chat.queries:
                await chat_service.update_query_response(
                    db,
                    chat.queries[0].id,
                    response_text,
                    ", ".join(agent_names),
                    token_usage
                )
            
            logger.info(f"💾 Chat saved to database with ID: {chat.id}")
            
        except Exception as save_error:
            # Don't fail the request if database saving fails
            logger.warning(f"⚠️ Failed to save chat to database: {save_error}")

        return ChatResponse(
            response=response_text,
            token_usage=token_usage,
            agent_used=", ".join(agent_names),
        )
    except Exception as e:
        logger.exception(traceback.format_exc())
    
        # Check for GitHub-specific errors
        if "401" in str(e) and "github" in str(e).lower():
            raise HTTPException(
                status_code=401, 
                detail="GitHub authentication required. Use /auth/github/login to get access token."
            )
        elif "403" in str(e) and "github" in str(e).lower():
            raise HTTPException(
                status_code=403,
                detail="GitHub token lacks required permissions. Ensure 'repo' scope is granted."
            )
        elif "502" in str(e) or "Bad Gateway" in str(e):
            raise HTTPException(
                status_code=413,
                detail="Request too large. Try with smaller PDF files or more specific queries."
            )
        
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)[:200]}")