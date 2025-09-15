from llama_index.core.prompts import ChatMessage, MessageRole
from datetime import datetime
from typing import List, Optional

# 🚨 CRITICAL: Reduce limits further
MAX_TOOL_DESC = 100  # Down from 1000 - just tool names basically
MAX_SYSTEM_PROMPT_CHARS = 800  # Down from 2000 - ultra conservative
MAX_TOOLS_IN_PROMPT = 6  # Down from 10 - only essential tools

def get_system_prompt(
    tool_descriptions: List[str],
    agent_names: List[str],
    has_pdf_context: bool = False,
    pdf_summary: Optional[str] = None,
) -> ChatMessage:
    """Generate an ultra-minimal system prompt for the ReAct agent."""

    # 🔧 OPTIMIZATION 1: Extract only tool NAMES, not full descriptions
    tool_names: List[str] = []
    for desc in tool_descriptions[:MAX_TOOLS_IN_PROMPT]:
        # Extract just the tool name (before first colon or parenthesis)
        tool_name = desc.split(":")[0].split("(")[0].strip()
        if tool_name and len(tool_name) < 40:  # Avoid overly long names
            tool_names.append(tool_name)
    
    # 🔧 OPTIMIZATION 2: Comma-separated instead of bullet points
    tools_str = ", ".join(tool_names[:6])  # Max 6 tool names
    agent_label = agent_names[0] if agent_names else "Assistant"  # Just first agent

    # 🔧 OPTIMIZATION 3: Remove PDF context entirely for GitHub queries
    pdf_section = ""
    if has_pdf_context and "github" not in agent_label.lower():
        pdf_section = " PDF uploaded."

    # 🔧 OPTIMIZATION 4: Ultra-minimal system prompt
    system_text = f"""AI assistant. Tools: {tools_str}.{pdf_section}

Use tools to answer queries. Be concise."""

    # 🔧 OPTIMIZATION 5: Emergency truncation with buffer
    if len(system_text) > MAX_SYSTEM_PROMPT_CHARS:
        # More aggressive truncation
        system_text = f"AI assistant. Tools: {tools_str[:200]}. Use tools for queries."
        
    return ChatMessage(role=MessageRole.SYSTEM, content=system_text)