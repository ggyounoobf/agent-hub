"""
🚀 Speed Optimizer for Agent Hub
Implements ultra-fast query processing with tool pre-filtering and prompt optimization.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.config.settings import *

logger = logging.getLogger(__name__)

class SpeedOptimizer:
    """Optimizes agent execution for GPT-level response speeds"""
    
    # Pre-defined tool mappings for common query patterns
    QUERY_PATTERNS = {
        # GitHub Security Patterns
        r'(?i)(dependabot|vulnerable|vulnerability|alert)': {
            'tools': ['list_dependabot_alerts', 'get_dependabot_alert'],
            'agent': 'github_security_agent',
            'max_tools': 5
        },
        r'(?i)(codeql|code scan|security scan|alert)': {
            'tools': ['list_code_scanning_alerts', 'get_code_scanning_alert'],
            'agent': 'github_security_agent', 
            'max_tools': 5
        },
        r'(?i)(secret|leaked|credential)': {
            'tools': ['list_secret_scanning_alerts', 'get_secret_scanning_alert'],
            'agent': 'github_security_agent',
            'max_tools': 5
        },
        
        # GitHub General Patterns
        r'(?i)(pull request|pr|merge)': {
            'tools': ['list_pull_requests', 'get_pull_request', 'create_pull_request'],
            'agent': 'github_agent',
            'max_tools': 8
        },
        r'(?i)(issue|bug|feature)': {
            'tools': ['list_issues', 'get_issue', 'create_issue'],
            'agent': 'github_agent',
            'max_tools': 8
        },
        r'(?i)(repository|repo|fork|clone)': {
            'tools': ['get_repository', 'list_repositories', 'create_repository'],
            'agent': 'github_agent',
            'max_tools': 10
        },
        
        # Snyk Patterns
        r'(?i)(snyk|scan|security scan)': {
            'tools': ['snyk_scan_github_repo', 'snyk_scan_docker_image'],
            'agent': 'snyk_scanner_agent',
            'max_tools': 3
        },
        
        # Chart Patterns  
        r'(?i)(chart|graph|visual|plot|dashboard)': {
            'tools': ['create_chart', 'render_chart'],
            'agent': 'chart_agent',
            'max_tools': 3
        }
    }
    
    def optimize_for_speed(self, query: str, available_agents: List[str], all_tools: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any], Dict[str, Any]]:
        """
        Ultra-fast optimization: pre-filter tools and agents based on query patterns
        
        Returns:
            - optimized_agents: List of best agents for this query
            - filtered_tools: Only relevant tools (dramatically reduced set)
            - speed_config: Configuration for fastest execution
        """
        logger.info(f"🚀 Speed optimizing query: {query[:100]}...")
        
        # Step 1: Pattern matching for instant tool selection
        best_match = self._match_query_pattern(query)
        
        if best_match:
            # Fast path: we know exactly what tools to use
            optimized_agents = [best_match['agent']] if best_match['agent'] in available_agents else available_agents[:1]
            filtered_tools = self._filter_tools_by_names(all_tools, best_match['tools'])
            
            logger.info(f"🎯 Fast path: matched pattern for {best_match['agent']}")
            if len(all_tools) > 0:
                logger.info(f"🔧 Reduced tools: {len(all_tools)} → {len(filtered_tools)} ({(1-len(filtered_tools)/len(all_tools))*100:.1f}% reduction)")
            else:
                logger.info(f"🔧 Tool filtering will be applied during agent building")
            
        else:
            # Fallback: smart agent selection + tool filtering
            optimized_agents = self._select_best_agents(query, available_agents)
            filtered_tools = self._filter_tools_by_relevance(all_tools, query, max_tools=15)
            
            logger.info(f"🤖 Smart path: selected {len(optimized_agents)} agents")
            if len(all_tools) > 0:
                logger.info(f"🔧 Filtered tools: {len(all_tools)} → {len(filtered_tools)} ({(1-len(filtered_tools)/len(all_tools))*100:.1f}% reduction)")
            else:
                logger.info(f"🔧 Tool filtering will be applied during agent building")
        
        # Step 2: Speed configuration
        speed_config = {
            'max_iterations': 3,  # Ultra-low for speed
            'temperature': 0.0,   # Deterministic responses
            'timeout': 30,        # Quick timeout
            'parallel_tools': True,  # Enable parallel tool calls
            'stream': True,       # Stream responses
            'verbose': False,     # Reduce verbosity for speed
            'max_tools': best_match.get('max_tools', 15) if best_match else 15,  # Tool limit
            'desc_limit': 100,    # Shorter descriptions
            'tool_warning_threshold': 15  # Lower warning threshold
        }
        
        return optimized_agents, filtered_tools, speed_config
    
    def _match_query_pattern(self, query: str) -> Optional[Dict[str, Any]]:
        """Match query against pre-defined patterns for instant optimization"""
        for pattern, config in self.QUERY_PATTERNS.items():
            if re.search(pattern, query):
                logger.info(f"✅ Matched pattern: {pattern}")
                return config
        return None
    
    def _filter_tools_by_names(self, all_tools: Dict[str, Any], tool_names: List[str]) -> Dict[str, Any]:
        """Filter tools to only include specific tool names"""
        filtered = {}
        for tool_name, tool_obj in all_tools.items():
            # Match tool names (partial matching for flexibility)
            for target_name in tool_names:
                if target_name in tool_name or any(word in tool_name for word in target_name.split('_')):
                    filtered[tool_name] = tool_obj
                    break
        return filtered
    
    def _filter_tools_by_relevance(self, all_tools: Dict[str, Any], query: str, max_tools: int = 15) -> Dict[str, Any]:
        """Filter tools by relevance scoring"""
        query_words = set(query.lower().split())
        
        # Score tools by relevance
        tool_scores = []
        for tool_name, tool_obj in all_tools.items():
            score = self._calculate_tool_relevance(tool_name, tool_obj, query_words)
            tool_scores.append((score, tool_name, tool_obj))
        
        # Sort by score and take top N
        tool_scores.sort(reverse=True)
        filtered = {}
        for score, tool_name, tool_obj in tool_scores[:max_tools]:
            if score > 0:  # Only include tools with some relevance
                filtered[tool_name] = tool_obj
        
        return filtered
    
    def _calculate_tool_relevance(self, tool_name: str, tool_obj: Any, query_words: set) -> float:
        """Calculate relevance score for a tool"""
        score = 0.0
        
        # Tool name matching
        tool_words = set(tool_name.lower().replace('_', ' ').split())
        score += len(query_words.intersection(tool_words)) * 3
        
        # Description matching (if available)
        if hasattr(tool_obj, 'description') and tool_obj.description:
            desc_words = set(tool_obj.description.lower().split())
            score += len(query_words.intersection(desc_words)) * 2
        
        # Common action words
        action_words = {'list', 'get', 'create', 'update', 'delete', 'scan', 'check'}
        if any(word in tool_name.lower() for word in action_words):
            score += 1
        
        return score
    
    def _select_best_agents(self, query: str, available_agents: List[str]) -> List[str]:
        """Select best agents for query (fallback when no pattern matches)"""
        query_lower = query.lower()
        
        # Priority mapping
        agent_priorities = {
            'github_security_agent': ['security', 'vulnerability', 'alert', 'dependabot', 'codeql', 'secret'],
            'github_agent': ['github', 'repository', 'pull', 'issue', 'commit'],
            'snyk_scanner_agent': ['snyk', 'scan', 'vulnerability'],
            'chart_agent': ['chart', 'graph', 'visual', 'plot']
        }
        
        # Score agents
        agent_scores = []
        for agent in available_agents:
            score = 0
            if agent in agent_priorities:
                for keyword in agent_priorities[agent]:
                    if keyword in query_lower:
                        score += 1
            agent_scores.append((score, agent))
        
        # Sort by score and return top 1-2 agents
        agent_scores.sort(reverse=True)
        return [agent for score, agent in agent_scores[:2] if score > 0] or available_agents[:1]

# Global instance
speed_optimizer = SpeedOptimizer()
