# app/utils/agent_utils.py

from typing import List, Union, Optional, Dict
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms import LLM
from llama_index.core.tools import BaseTool, FunctionTool
from llama_index.core.callbacks.base import CallbackManager
from llama_index.core.prompts.base import ChatPromptTemplate
import logging
from app.config import LLM_MEMORY_TOKEN_LIMIT
from app.prompts.system_prompts import get_system_prompt

logger = logging.getLogger(__name__)

def estimate_tokens(text: str) -> int:
    """Rough token estimation (1.3 tokens per word)."""
    return int(len(text.split()) * 1.3)

def build_agent(
    tools: List[Union[FunctionTool, BaseTool]],
    llm: LLM,
    callback_manager: CallbackManager,
    prompt_template: Optional[ChatPromptTemplate] = None,
    agent_names: Optional[List[str]] = None,
    has_pdf_context: bool = False,
    pdf_summary: Optional[str] = None,
) -> ReActAgent:
    """Constructs a ReActAgent with robust prompt handling and token management."""

    logger.info("Building agent with %d tools", len(tools))
    system_prompt_content: Optional[str] = None

    # Helper: safe metadata (some MCP tools lack description/name or have very long text)
    def _safe_meta(t: Union[FunctionTool, BaseTool]) -> tuple[str, str]:
        md = getattr(t, "metadata", None)
        name = getattr(md, "name", None) or "unnamed_tool"
        desc = getattr(md, "description", "") or "No description."
        if len(desc) > 1000:
            desc = desc[:1000] + "…"
        return name, desc

    if prompt_template is None:
        tool_descriptions = [f"{n}: {d}" for (n, d) in map(_safe_meta, tools)]
        agent_names = agent_names or ["dynamic_agent"]

        # Strict PDF summary truncation for token management
        truncated_pdf_summary = None
        if pdf_summary and has_pdf_context:
            max_summary_chars = 800  # conservative limit
            if len(pdf_summary) > max_summary_chars:
                truncated_pdf_summary = (
                    pdf_summary[:max_summary_chars]
                    + "\n\n[Summary truncated. Use PDF tools for full content.]"
                )
                logger.warning(
                    "PDF summary truncated: %d → %d chars",
                    len(pdf_summary),
                    len(truncated_pdf_summary),
                )
            else:
                truncated_pdf_summary = pdf_summary

        system_message = get_system_prompt(
            tool_descriptions=tool_descriptions,
            agent_names=agent_names,
            has_pdf_context=has_pdf_context,
            pdf_summary=truncated_pdf_summary,
        )
        system_prompt_content = (
            system_message.content
            if hasattr(system_message, "content")
            else str(system_message)
        )
    else:
        # Extract a system message from a provided ChatPromptTemplate
        try:
            msgs = getattr(prompt_template, "message_templates", None) or getattr(
                prompt_template, "messages", []
            )
            for m in msgs:
                role = str(getattr(m, "role", "")).lower()
                if "system" in role:
                    system_prompt_content = getattr(m, "content", None) or str(m)
                    break
        except Exception as e:
            logger.warning(f"Failed to extract system prompt: {e}")

    # Fallback system prompt if nothing was extracted/generated
    if not system_prompt_content or system_prompt_content.strip() == "":
        tool_names = [
            getattr(getattr(t, "metadata", None), "name", "unknown")
            for t in tools
        ]
        tools_str = ", ".join(tool_names[:5])  # limit listed tools
        system_prompt_content = (
            f"You are a helpful AI assistant with access to tools: {tools_str}. "
            f"Use them to answer questions effectively."
        )

    # Enforce system prompt size limits
    max_chars = 6000  # conservative limit
    if len(system_prompt_content) > max_chars:
        logger.warning(
            "System prompt too long (%d chars), truncating",
            len(system_prompt_content),
        )
        system_prompt_content = system_prompt_content[: max_chars - 100] + "\n[Prompt truncated]"

    # Token budgeting (model-aware)
    model_limit = max(LLM_MEMORY_TOKEN_LIMIT or 32768, 8192)
    reserve = min(int(model_limit * 0.35), 12000)  # ~35% or cap at 12k
    available_memory = max(model_limit - reserve, 4096)

    estimated_tokens = estimate_tokens(system_prompt_content)
    logger.info(
        "System prompt: %d chars (~%d tokens) | Memory buffer: %d tokens",
        len(system_prompt_content),
        estimated_tokens,
        available_memory,
    )

    memory = ChatMemoryBuffer.from_defaults(token_limit=available_memory)
    
    try:
        agent = ReActAgent(
            tools=tools,
            llm=llm,
            system_prompt=system_prompt_content,
            verbose=True,
            callback_manager=callback_manager,
            memory=memory,
        )
        # Expose tools for downstream composition (your dynamic builder relies on this)
        setattr(agent, "tools", tools)
        return agent
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        # Minimal fallback
        agent = ReActAgent(
            tools=tools,
            llm=llm,
            system_prompt="You are a helpful AI assistant.",
            verbose=False,
            callback_manager=callback_manager,
            memory=ChatMemoryBuffer.from_defaults(token_limit=5000),
        )
        setattr(agent, "tools", tools)
        return agent
