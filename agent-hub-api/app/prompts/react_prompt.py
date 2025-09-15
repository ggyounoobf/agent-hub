from llama_index.core.prompts import ChatPromptTemplate
from .system_prompts import get_system_prompt
from .user_prompts import get_user_prompt
from typing import List, Optional

def get_mcp_chat_prompt(
    tool_descriptions: List[str], 
    agent_names: List[str],
    has_pdf_context: bool = False,
    pdf_summary: Optional[str] = None
) -> ChatPromptTemplate:
    """
    Create a ChatPromptTemplate for MCP agents with optional PDF context.
    
    Args:
        tool_descriptions: List of tool descriptions
        agent_names: List of agent names
        has_pdf_context: Whether PDF context is present
        pdf_summary: Summary of PDF files
        
    Returns:
        ChatPromptTemplate instance
    """
    return ChatPromptTemplate(
        message_templates=[
            get_system_prompt(
                tool_descriptions, 
                agent_names,
                has_pdf_context=has_pdf_context,
                pdf_summary=pdf_summary
            ),
            get_user_prompt()
        ]
    )

# Keep backward compatibility for existing code
def get_mcp_chat_prompt_simple(tool_descriptions: List[str], agent_names: List[str]) -> ChatPromptTemplate:
    """Backward compatible version without PDF support."""
    return get_mcp_chat_prompt(tool_descriptions, agent_names, has_pdf_context=False)