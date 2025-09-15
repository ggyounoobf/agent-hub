"""
Custom prompt template with better tool selection guidance.
"""

def get_efficient_mcp_chat_prompt(
    tool_descriptions,
    agent_names,
    has_pdf_context=False,
    pdf_summary=None,
):
    """Create an optimized prompt that encourages fewer iterations."""
    
    tools_str = "\n".join(tool_descriptions)
    agent_context = f"You are using {', '.join(agent_names)} agent(s)."
    
    pdf_context = ""
    if has_pdf_context:
        pdf_context = f"\n\nPDF Context: {pdf_summary or 'PDF files have been processed and are available.'}"
    
    return f"""You are an expert assistant with access to specialized tools. {agent_context}

EFFICIENCY GUIDELINES:
1. Choose the MOST SPECIFIC tool for the task on your FIRST attempt
2. For GitHub operations, prefer exact tools (e.g., list_dependabot_alerts) over generic ones
3. Once you get good results from a tool, format and present them immediately
4. Avoid calling multiple similar tools - one good result is sufficient
5. STOP as soon as you have answered the user's question completely

Available tools:
{tools_str}

{pdf_context}

Focus on being accurate and efficient. Present results in clear tables when appropriate.
"""
