# app/agent_loader.py

from typing import Dict, List, Optional, Sequence
from llama_index.core.agent.workflow import ReActAgent
import os
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler
from llama_index.core.tools import BaseTool
from app.callbacks.tool_logger import ToolUsageLogger
from app.utils.agent_utils import build_agent
from app.services.agent_sync_service import AgentSyncService
from app.prompts import get_mcp_chat_prompt
from app.prompts.speed_prompts import get_speed_optimized_prompt, get_query_type
from app.config import (
    LLM_PROVIDER,
    MCP_URL,
    MCP_BEARER_TOKEN,
    GITHUB_TOKEN,
    validate_llm_config,
    get_llm_display_name,
    AZURE_SUBSCRIPTION_ID,
    AZURE_TENANT_ID,
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    SNYK_TOKEN,
    SNYK_ORG

)
from app.llm_factory import create_llm
from app.utils.logging import setup_logging
from app.agents.tool_utils import dedupe_tools_by_name, filter_tools_by_keywords
from app.agents.agent_builders import add_agent, AgentInfo
from sqlalchemy.ext.asyncio import AsyncSession

logger = setup_logging(__name__)

GITHUB_REMOTE_MCP_URL = "https://api.githubcopilot.com/mcp/"
CHART_REMOTE_MCP_URL = "http://localhost:1122/mcp"


def create_callback_manager() -> CallbackManager:
    """Create a standardized callback manager with token counting and tool logging."""
    token_handler = TokenCountingHandler()
    tool_logger = ToolUsageLogger()
    return CallbackManager([token_handler, tool_logger])


async def _load_github_mcp_tools(github_token: Optional[str]) -> List[BaseTool]:
    """Load tools from GitHub's hosted MCP (remote)."""
    if not github_token:
        logger.warning("🔑 No GitHub token provided; skipping GitHub hosted MCP tools.")
        return []

    try:
        client = BasicMCPClient(
            GITHUB_REMOTE_MCP_URL,
            headers={"Authorization": f"Bearer {github_token}"},
        )
        spec = McpToolSpec(client=client)
        tools = await spec.to_tool_list_async()
        valid: List[BaseTool] = [t for t in tools if isinstance(t, BaseTool)]
        logger.info("✅ Loaded %d GitHub hosted MCP tools", len(valid))
        return valid
    except Exception as e:
        logger.warning(f"⚠️ GitHub hosted MCP tools not available: {e}")
        return []


async def _load_chart_mcp_tools() -> List[BaseTool]:
    """Load tools from the local Chart MCP server."""
    try:
        client = BasicMCPClient(CHART_REMOTE_MCP_URL)
        spec = McpToolSpec(client=client)
        tools = await spec.to_tool_list_async()
        valid: List[BaseTool] = [t for t in tools if isinstance(t, BaseTool)]
        logger.info("✅ Loaded %d Chart MCP tools", len(valid))
        return valid
    except Exception as e:
        logger.warning(f"⚠️ Chart MCP tools not available: {e}")
        return []


async def _load_azure_mcp_tools() -> List[BaseTool]:
    """Load tools from Azure MCP stdio server with Service Principal authentication."""
    required_vars = {
        "AZURE_SUBSCRIPTION_ID": AZURE_SUBSCRIPTION_ID,
        "AZURE_TENANT_ID": AZURE_TENANT_ID,
        "AZURE_CLIENT_ID": AZURE_CLIENT_ID,
        "AZURE_CLIENT_SECRET": AZURE_CLIENT_SECRET,
    }

    # 🔎 Check if all required environment variables are set
    missing = [k for k, v in required_vars.items() if not v]
    if missing:
        logger.warning(f"⚠️ Skipping Azure MCP tools — missing env vars: {', '.join(missing)}")
        return []

    try:
        # Inherit existing environment and inject Service Principal creds
        env_vars = {**os.environ, **required_vars}

        # Start Azure MCP server via npx with env credentials
        local_client = BasicMCPClient(
            "npx",
            args=["-y", "@azure/mcp@latest", "server", "start"],
            env=env_vars,
        )

        # Discover tools
        spec = McpToolSpec(client=local_client)
        tools = await spec.to_tool_list_async()

        valid: List[BaseTool] = [t for t in tools if isinstance(t, BaseTool)]
        logger.info("✅ Loaded %d Azure MCP tools", len(valid))
        return valid

    except Exception as e:
        logger.warning(f"⚠️ Azure MCP tools not available: {e}")
        return []





async def load_agents(db: AsyncSession, github_token: Optional[str] = None) -> Dict[str, AgentInfo]:
    """
    Load and initialize all predefined agents with their specialized tools.
    """
    agents: Dict[str, AgentInfo] = {}

    # Validate LLM config
    if not validate_llm_config():
        raise ValueError(f"Missing {LLM_PROVIDER.value} config in environment.")

    logger.info("🤖 Using LLM Provider: %s", get_llm_display_name())

    # Shared components
    callback_manager = create_callback_manager()
    llm = create_llm(callback_manager)

    # Use provided token or fallback
    effective_github_token = github_token or GITHUB_TOKEN

    # --- 1) GitHub MCP tools ---
    github_remote_tools: List[BaseTool] = await _load_github_mcp_tools(effective_github_token)

    # --- 2) Chart MCP tools ---chart_tools: List[BaseTool] = await _load_chart_mcp_tools()
    chart_tools: List[BaseTool] = await _load_chart_mcp_tools()

    # --- 3) Base MCP server tools ---
    base_client = BasicMCPClient(
        MCP_URL,
        headers={"Authorization": f"Bearer {MCP_BEARER_TOKEN}"},
    )
    # --- 2) Azure MCP tools ---chart_tools: List[BaseTool] = await _load_azure_mcp_tools()
    azure_tools: List[BaseTool] = await _load_azure_mcp_tools()

    base_spec = McpToolSpec(client=base_client)
    base_tools_raw = await base_spec.to_tool_list_async()
    base_tools: List[BaseTool] = [t for t in base_tools_raw if isinstance(t, BaseTool)]
    logger.info("🔧 Loaded %d base MCP tools", len(base_tools))

    # --- GitHub Agent ---
    github_base_tools = filter_tools_by_keywords(base_tools, ["github"])
    all_github_tools = dedupe_tools_by_name(github_remote_tools + github_base_tools)
    add_agent(
        agents,
        "github_agent",
        "Specialized agent for GitHub operations including workflows, repositories, issues, and pull requests",
        all_github_tools,
        llm,
        callback_manager,
    )
    # --- Azure Agent ---
    add_agent(
        agents,
        "azure_agent",
        "Agent for connecting Azure.",
        azure_tools,
        llm,
        callback_manager,
    )
    # --- Chart Agent ---
    add_agent(
        agents,
        "chart_agent",
        "Agent for creating charts.",
        chart_tools,
        llm,
        callback_manager,
    )

    # --- Database Agent ---
    # add_agent(
    #     agents,
    #     "database_agent",
    #     filter_tools_by_keywords(base_tools, ["db", "database", "sql"]),
    #     llm,
    #     callback_manager,
    # )

    # --- Sample Agent ---
    add_agent(
        agents,
        "sample_agent",
        "Agent for testing and sample operations",
        filter_tools_by_keywords(base_tools, ["sample"]),
        llm,
        callback_manager,
    )

    # --- PDF Agent ---
    add_agent(
        agents,
        "pdf_agent", 
        "Specialized agent for PDF document processing, text extraction, and content analysis",
        filter_tools_by_keywords(base_tools, ["pdf"]),
        llm,
        callback_manager,
    )

    # --- Security Agent ---
    add_agent(
        agents,
        "security_agent",
        "Agent for web security",
        filter_tools_by_keywords(base_tools, ["security"]),
        llm,
        callback_manager,
    )

    # --- GitHub + Snyk Combined Agent ---
    github_snyk_tools = dedupe_tools_by_name(
        all_github_tools + filter_tools_by_keywords(base_tools, ["snyk"])
    )
    add_agent(
        agents,
        "github_security_agent",
        "Combined agent for GitHub operations and Snyk security scanning. Can clone repositories and perform vulnerability analysis.",
        github_snyk_tools,
        llm,
        callback_manager,
    )

    # --- Snyk Scanner Agent ---
    add_agent(
        agents,
        "snyk_scanner_agent",
        "Specialized agent for Snyk security vulnerability scanning and analysis",
        filter_tools_by_keywords(base_tools, ["snyk"]),
        llm,
        callback_manager,
    )

    # Remove PDF, and other specialized tools from scrape agent
    excluded_tools = []
    for tool in base_tools:
        tool_name = str(getattr(getattr(tool, "metadata", None), "name", "")).lower()
        # Exclude specialized tools
        if not any(keyword in tool_name for keyword in ["pdf"]):
            excluded_tools.append(tool)

    # Keep only scrape tools for scrape agent
    add_agent(
        agents,
        "scraper_agent",
        "Agent for web scraping and content extraction",
        filter_tools_by_keywords(base_tools, ["scrape", "extract"]),
        llm,
        callback_manager,
    )

    # --- 5) Admin agent removed as per requirements ---
    # all_tools_for_admin = list(base_tools)
    # all_tools_for_admin.extend(github_remote_tools)
    # all_tools_for_admin = dedupe_tools_by_name(all_tools_for_admin)
    # 
    # logger.warning("🚨 Admin agent will have %d total tools - may cause context overflow!", len(all_tools_for_admin))
    # 
    # add_agent(
    #     agents,
    #     "admin_agent",
    #     "Admin have access to all the tools",
    #     all_tools_for_admin,
    #     llm,
    #     callback_manager,
    # )

    # --- 6) Log tool distribution summary ---
    logger.info("📊 Tool Distribution Summary:")
    for agent_name, agent in agents.items():
        tool_count = len(getattr(agent, "tools", []))
        logger.info(f"   {agent_name}: {tool_count} tools")


    # --- 7) Add all agents to the database ---
    await AgentSyncService.sync_agents_to_db(agents, db)

    return agents


async def build_dynamic_agent(
    agent_names: List[str],
    agents: Dict[str, ReActAgent],
    has_pdf_context: bool = False,
    pdf_summary: Optional[str] = None,
) -> ReActAgent:
    """
    Build a dynamic agent by combining tools from multiple existing agents.

    NOTE: GitHub tools are already loaded during load_agents (if token was provided).
    You can still pass github_token here to *enhance/replace* GH tools per request, e.g., for user-specific OAuth.

    Args:
        agent_names: List of agent names to combine tools from.
        agents: Dictionary of existing agents.
        has_pdf_context: Whether PDF files are being processed.
        pdf_summary: Summary of PDF files if applicable.

    Returns:
        ReActAgent: New agent with combined tools from specified agents.

    Raises:
        ValueError: If no matching agents or no valid tools found.
    """
    # Check if agent names exist in available agents
    if not any(name in agents for name in agent_names):
        raise ValueError(f"No matching agents found for: {agent_names}")

    selected_tools: List[BaseTool] = []
    for name in agent_names:
        if name in agents:
            tools = getattr(agents[name], "tools", [])
            valid_tools = [t for t in tools if isinstance(t, BaseTool)]
            logger.info("📦 Agent '%s' contributed %d tools.", name, len(valid_tools))
            selected_tools.extend(valid_tools)
        else:
            logger.warning("⚠️ Agent '%s' not found in available agents.", name)

    if not selected_tools:
        raise ValueError("No valid agents or tools found.")

    unique_tools = dedupe_tools_by_name(selected_tools)
    logger.info("🧰 Loaded %d unique tools from agents: %s", len(unique_tools), agent_names)

    # Create prompt with tool descriptions, agent context, and PDF context
    tool_descriptions: List[str] = []
    for t in unique_tools:
        md = getattr(t, "metadata", None)
        name = getattr(md, "name", None) or "unnamed_tool"
        desc = getattr(md, "description", "") or "No description."
        
        # 🚀 Aggressive truncation for rate limit optimization
        if len(desc) > 100:  # Reduced from 200 to 100
            desc = desc[:100] + "..."
            
        tool_descriptions.append(f"{name}: {desc}")

    # 🚀 Much stricter tool limit for rate limiting
    if len(tool_descriptions) > 30:  # Reduced from 50 to 30
        logger.warning(f"🚨 Too many tools ({len(tool_descriptions)}) - this may cause rate limits")
        logger.info("💡 Consider using fewer agents or more specific tool filtering")
        
        # 🎯 Smart tool selection - prioritize essential GitHub tools
        essential_tools = []
        other_tools = []
        
        essential_patterns = [
            'list_dependabot_alerts', 'get_dependabot_alert',
            'list_code_scanning_alerts', 'get_code_scanning_alert', 
            'list_secret_scanning_alerts', 'get_secret_scanning_alert',
            'list_issues', 'get_issue', 'create_issue',
            'list_pull_requests', 'get_pull_request', 'create_pull_request',
            'get_repository', 'list_repositories'
        ]
        
        for i, tool in enumerate(unique_tools):
            tool_name = getattr(getattr(tool, "metadata", None), "name", "").lower()
            if any(pattern in tool_name for pattern in essential_patterns):
                essential_tools.append((i, tool))
            else:
                other_tools.append((i, tool))
        
        # Keep essential tools + fill remaining slots
        selected_indices = []
        selected_tools = []
        selected_descriptions = []
        
        # Take all essential tools first
        for i, tool in essential_tools[:25]:  # Reserve 25 slots for essential
            selected_indices.append(i)
            selected_tools.append(tool)
            selected_descriptions.append(tool_descriptions[i])
        
        # Fill remaining slots with other tools
        remaining_slots = 30 - len(selected_tools)
        for i, tool in other_tools[:remaining_slots]:
            selected_indices.append(i)
            selected_tools.append(tool)
            selected_descriptions.append(tool_descriptions[i])
        
        unique_tools = selected_tools
        tool_descriptions = selected_descriptions
        
        logger.info(f"🚀 Smart tool selection: {len(essential_tools)} essential + {len(selected_tools) - len(essential_tools)} others = {len(selected_tools)} total")
        
        # Log which essential tools we kept
        essential_names = [getattr(getattr(tool, "metadata", None), "name", "") for _, tool in essential_tools[:25]]
        logger.info(f"🎯 Essential tools included: {', '.join(essential_names[:10])}...")
    else:
        logger.info(f"✅ Tool count ({len(tool_descriptions)}) is within limits")

    # 🚀 Speed optimization: Use ultra-fast prompts for common queries
    # Note: Disabled speed prompts for now - tool filtering is more effective
    if False:  # Disabled for functionality
        pass
    else:
        # Default behavior - use regular prompt
        prompt = get_mcp_chat_prompt(
            tool_descriptions,
            agent_names,
            has_pdf_context=has_pdf_context,
            pdf_summary=pdf_summary,
        )

    callback_manager = create_callback_manager()
    llm = create_llm(callback_manager)

    return build_agent(
        tools=unique_tools,
        llm=llm,
        callback_manager=callback_manager,
        prompt_template=prompt,
        agent_names=agent_names,
        has_pdf_context=has_pdf_context,
        pdf_summary=pdf_summary,
    )