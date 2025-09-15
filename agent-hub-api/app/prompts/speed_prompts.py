"""
⚡ Ultra-Fast Prompt Templates
Optimized prompts for instant responses to common queries.
"""

def get_speed_optimized_prompt(query_type: str, tools: list) -> str:
    """Get optimized prompt for specific query types"""
    
    if query_type == "dependabot":
        return f"""You are a GitHub security specialist. Focus ONLY on Dependabot vulnerability management.

Available tools: {[tool.metadata.name for tool in tools[:5]]}

Guidelines:
- Use list_dependabot_alerts for vulnerability queries
- Be direct and concise
- Format results in tables
- ONE tool call maximum
- No explanations unless asked

User query will follow."""

    elif query_type == "codeql":
        return f"""You are a GitHub security specialist. Focus ONLY on CodeQL security scanning.

Available tools: {[tool.metadata.name for tool in tools[:5]]}

Guidelines:
- Use list_code_scanning_alerts for scan queries  
- Be direct and concise
- Format results in tables
- ONE tool call maximum
- No explanations unless asked

User query will follow."""

    elif query_type == "github_general":
        return f"""You are a GitHub specialist. Focus on repository management.

Available tools: {[tool.metadata.name for tool in tools[:8]]}

Guidelines:
- Choose the most relevant tool
- Be direct and concise
- Format results clearly
- Maximum 2 tool calls
- No explanations unless asked

User query will follow."""

    else:
        # Ultra-minimal default prompt
        return f"""You are an AI assistant. Use the available tools to answer the user's query directly and concisely.

Available tools: {[tool.metadata.name for tool in tools[:10]]}

Be direct. No unnecessary explanations. Format results clearly."""

def get_query_type(query: str) -> str:
    """Determine query type for prompt optimization"""
    query_lower = query.lower()
    
    if any(word in query_lower for word in ['dependabot', 'vulnerability', 'vulnerable', 'dependency']):
        return "dependabot"
    elif any(word in query_lower for word in ['codeql', 'code scan', 'security scan', 'alert']):
        return "codeql"
    elif any(word in query_lower for word in ['github', 'repository', 'repo', 'pull', 'issue']):
        return "github_general"
    else:
        return "general"
