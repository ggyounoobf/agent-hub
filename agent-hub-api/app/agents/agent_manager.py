from typing import Dict, List, Optional, Any
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.tools import BaseTool
from app.utils.logging import setup_logging

logger = setup_logging(__name__)

class AgentManager:
    """Centralized agent management utilities."""
    
    def __init__(self, agents: Dict[str, ReActAgent]):
        self.agents = agents
    
    def get_agent_info(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific agent."""
        if agent_name not in self.agents:
            return None
        
        agent = self.agents[agent_name]
        tools = getattr(agent, 'tools', [])
        tool_names = [getattr(t.metadata, 'name', 'unknown') for t in tools]
        
        # Safe memory check - ReActAgent might store memory differently
        has_memory = False
        try:
            # Try different possible memory attribute names
            memory = getattr(agent, 'memory', None)
            if memory is None:
                memory = getattr(agent, '_memory', None)
            if memory is None:
                memory = getattr(agent, 'chat_memory', None)
            has_memory = memory is not None
        except Exception:
            has_memory = False
        
        return {
            'name': agent_name,
            'tool_count': len(tools),
            'tool_names': tool_names,
            'has_llm': hasattr(agent, 'llm') and agent.llm is not None,
            'has_memory': has_memory,
            'verbose': getattr(agent, 'verbose', False),
            'agent_type': type(agent).__name__
        }
    
    def list_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all agents."""
        result = {}
        for name in self.agents.keys():
            agent_info = self.get_agent_info(name)
            if agent_info is not None:  # Only include non-None results
                result[name] = agent_info
        return result
    
    def remove_agent(self, agent_name: str) -> bool:
        """Remove an agent."""
        if agent_name in self.agents:
            del self.agents[agent_name]
            logger.info(f"🗑️ Removed agent '{agent_name}'")
            return True
        else:
            logger.warning(f"⚠️ Agent '{agent_name}' not found for removal")
            return False
    
    def agent_exists(self, agent_name: str) -> bool:
        """Check if agent exists."""
        return agent_name in self.agents
    
    def get_agent_names(self) -> List[str]:
        """Get list of all agent names."""
        return list(self.agents.keys())
    
    def get_tools_for_agent(self, agent_name: str) -> List[BaseTool]:
        """Get tools for a specific agent."""
        if agent_name not in self.agents:
            return []
        return getattr(self.agents[agent_name], 'tools', [])
    
    def find_agents_with_tool(self, tool_name: str) -> List[str]:
        """Find all agents that have a specific tool."""
        agents_with_tool = []
        for agent_name, agent in self.agents.items():
            tools = getattr(agent, 'tools', [])
            tool_names = [getattr(t.metadata, 'name', '') for t in tools]
            if tool_name in tool_names:
                agents_with_tool.append(agent_name)
        return agents_with_tool
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """Get overall statistics about all agents."""
        total_agents = len(self.agents)
        total_tools = 0
        all_tool_names = set()
        
        for agent in self.agents.values():
            tools = getattr(agent, 'tools', [])
            total_tools += len(tools)
            for tool in tools:
                tool_name = getattr(tool.metadata, 'name', 'unknown')
                all_tool_names.add(tool_name)
        
        return {
            'total_agents': total_agents,
            'total_tools': total_tools,
            'unique_tools': len(all_tool_names),
            'tool_names': sorted(all_tool_names)
        }
    
    def inspect_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Deep inspection of an agent's attributes (for debugging)."""
        if agent_name not in self.agents:
            return None
        
        agent = self.agents[agent_name]
        attributes = {}
        
        # Get all attributes of the agent
        for attr_name in dir(agent):
            if not attr_name.startswith('_'):  # Skip private attributes
                try:
                    attr_value = getattr(agent, attr_name)
                    # Don't include methods, just properties
                    if not callable(attr_value):
                        attributes[attr_name] = str(type(attr_value))
                except Exception:
                    attributes[attr_name] = "Error accessing attribute"
        
        return {
            'agent_name': agent_name,
            'agent_type': type(agent).__name__,
            'attributes': attributes
        }

# Standalone utility functions (for backward compatibility)
def get_agent_info(agent: ReActAgent) -> Dict[str, Any]:
    """Get information about an agent."""
    tools = getattr(agent, 'tools', [])
    tool_names = [getattr(t.metadata, 'name', 'unknown') for t in tools]
    
    # Safe memory check
    has_memory = False
    try:
        memory = getattr(agent, 'memory', None)
        if memory is None:
            memory = getattr(agent, '_memory', None)
        if memory is None:
            memory = getattr(agent, 'chat_memory', None)
        has_memory = memory is not None
    except Exception:
        has_memory = False
    
    return {
        'tool_count': len(tools),
        'tool_names': tool_names,
        'has_llm': hasattr(agent, 'llm') and agent.llm is not None,
        'has_memory': has_memory,
        'verbose': getattr(agent, 'verbose', False),
        'agent_type': type(agent).__name__
    }

def list_agents_info(agents: Dict[str, ReActAgent]) -> Dict[str, Dict[str, Any]]:
    """Get information about all agents."""
    return {name: get_agent_info(agent) for name, agent in agents.items()}

def remove_agent(agents: Dict[str, ReActAgent], agent_name: str) -> bool:
    """Remove an agent from the agents dictionary."""
    if agent_name in agents:
        del agents[agent_name]
        logger.info(f"🗑️ Removed agent '{agent_name}'")
        return True
    else:
        logger.warning(f"⚠️ Agent '{agent_name}' not found for removal")
        return False