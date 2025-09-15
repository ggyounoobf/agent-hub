# app/agents/agent_builders.py

from typing import Dict, List, Optional
from dataclasses import dataclass
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.llms import LLM
from llama_index.core.callbacks.base import CallbackManager
from llama_index.core.tools import BaseTool
from app.utils.agent_utils import build_agent
from app.prompts.react_prompt import get_mcp_chat_prompt
from app.utils.logging import setup_logging

logger = setup_logging(__name__)

@dataclass
class AgentInfo:
    """Container for agent with metadata."""
    agent: ReActAgent
    description: str
    tools: List[BaseTool]
    name: str

def prompt_for_agent(
    tools: List[BaseTool],
    agent_name: str,
    has_pdf_context: bool = False,
    pdf_summary: Optional[str] = None,
):
    """
    Create a prompt template for an agent with given tools.

    Raises:
        ValueError: If tools list is empty or agent_name is invalid
    """
    if not tools:
        raise ValueError(f"Cannot create prompt for agent '{agent_name}': no tools provided")

    if not agent_name or not agent_name.strip():
        raise ValueError("Agent name cannot be empty")

    descriptions: List[str] = []
    for i, tool in enumerate(tools):
        # Robust metadata extraction and clamping
        md = getattr(tool, "metadata", None)
        tool_name = getattr(md, "name", None) if md else None
        tool_desc = getattr(md, "description", None) if md else None

        if not tool_name:
            logger.warning(f"Tool at index {i} has no name, using 'tool_{i}'")
            tool_name = f"tool_{i}"

        if not tool_desc:
            logger.warning(f"Tool '{tool_name}' has no description")
            tool_desc = "No description available"

        # Clamp very long descriptions to keep prompt size reasonable
        if len(tool_desc) > 1000:
            tool_desc = tool_desc[:1000] + "…"

        descriptions.append(f"{tool_name}: {tool_desc}")

    logger.debug(f"Creating prompt for agent '{agent_name}' with {len(descriptions)} tools")

    return get_mcp_chat_prompt(
        tool_descriptions=descriptions,
        agent_names=[agent_name],
        has_pdf_context=has_pdf_context,
        pdf_summary=pdf_summary,
    )

def add_agent(
    agents: Dict[str, AgentInfo],  # Changed type
    agent_name: str,
    description: str,  # New parameter
    tools: List[BaseTool],
    llm: LLM,
    callback_manager: CallbackManager,
    has_pdf_context: bool = False,
    pdf_summary: Optional[str] = None,
) -> None:
    """
    Create and attach a ReActAgent for a given tool subset with description.
    """
    if not tools:
        logger.warning(f"⚠️ No tools provided for agent '{agent_name}'. Skipping.")
        return

    if not agent_name or not agent_name.strip():
        logger.error("Agent name cannot be empty")
        return

    if not description or not description.strip():
        logger.warning(f"⚠️ No description provided for agent '{agent_name}'. Using default.")
        description = f"Agent for {agent_name} operations"

    # Overwrite notice if name already present
    if agent_name in agents:
        logger.warning(f"⚠️ Agent '{agent_name}' already exists. Overwriting.")

    try:
        prompt = prompt_for_agent(
            tools,
            agent_name,
            has_pdf_context=has_pdf_context,
            pdf_summary=pdf_summary,
        )

        agent = build_agent(
            tools=tools,
            llm=llm,
            callback_manager=callback_manager,
            prompt_template=prompt,
            agent_names=[agent_name],
            has_pdf_context=has_pdf_context,
            pdf_summary=pdf_summary,
        )

        # Expose tools so composition code can introspect later
        try:
            setattr(agent, "tools", tools)
        except Exception:
            logger.debug("Agent object does not allow dynamic attrs; skipping tools attach.")

        # Store as AgentInfo with description
        agents[agent_name] = AgentInfo(
            agent=agent,
            description=description,
            tools=tools,
            name=agent_name
        )
        
        logger.info(f"✅ Agent '{agent_name}' loaded with {len(tools)} tools.")
        logger.info(f"📝 Description: {description}")

        # Log tool names for debugging
        tool_names = [getattr(getattr(t, "metadata", None), "name", "unknown") for t in tools]
        logger.debug(f"🧰 Tools for '{agent_name}': {', '.join(tool_names)}")

    except Exception as e:
        logger.error(f"❌ Failed to create agent '{agent_name}': {e}")
        raise ValueError(f"Failed to create agent '{agent_name}': {e}") from e

def add_agent_simple(
    agents: Dict[str, AgentInfo],  # Updated type
    agent_name: str,
    tools: List[BaseTool],
    llm: LLM,
    callback_manager: CallbackManager,
) -> None:
    """Backward compatible version of add_agent without PDF support."""
    add_agent(
        agents=agents,
        agent_name=agent_name,
        description=f"Agent for {agent_name} operations",  # Default description
        tools=tools,
        llm=llm,
        callback_manager=callback_manager,
        has_pdf_context=False,
        pdf_summary=None,
    )

def validate_agent_setup(
    agent_name: str,
    tools: List[BaseTool],
    llm: LLM,
    callback_manager: CallbackManager,
) -> bool:
    """
    Validate that all components needed for agent creation are valid.
    """
    if not agent_name or not agent_name.strip():
        raise ValueError("Agent name cannot be empty")

    if not tools:
        raise ValueError("Tools list cannot be empty")

    if llm is None:
        raise ValueError("LLM cannot be None")

    if callback_manager is None:
        raise ValueError("Callback manager cannot be None")

    # Validate each tool
    for i, tool in enumerate(tools):
        if not isinstance(tool, BaseTool):
            raise ValueError(f"Tool at index {i} is not a BaseTool instance")

        if not hasattr(tool, "metadata"):
            logger.warning(f"Tool at index {i} has no metadata")

    logger.debug(f"✅ Agent setup validation passed for '{agent_name}'")
    return True

def create_agent_with_validation(
    agent_name: str,
    tools: List[BaseTool],
    llm: LLM,
    callback_manager: CallbackManager,
    has_pdf_context: bool = False,
    pdf_summary: Optional[str] = None,
) -> ReActAgent:
    """
    Create a single agent with full validation (doesn't add to dictionary).
    """
    validate_agent_setup(agent_name, tools, llm, callback_manager)

    prompt = prompt_for_agent(
        tools,
        agent_name,
        has_pdf_context=has_pdf_context,
        pdf_summary=pdf_summary,
    )

    agent = build_agent(
        tools=tools,
        llm=llm,
        callback_manager=callback_manager,
        prompt_template=prompt,
        agent_names=[agent_name],
        has_pdf_context=has_pdf_context,
        pdf_summary=pdf_summary,
    )

    # Expose tools for downstream composition
    try:
        setattr(agent, "tools", tools)
    except Exception:
        logger.debug("Agent object does not allow dynamic attrs; skipping tools attach.")

    logger.info(f"✅ Created agent '{agent_name}' with {len(tools)} tools")
    return agent
