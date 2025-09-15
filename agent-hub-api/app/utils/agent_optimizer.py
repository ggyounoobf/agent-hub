"""
Agent recommendation and optimization utilities.
"""
from typing import List, Dict, Set
from app.utils.logging import setup_logging

logger = setup_logging(__name__)


class AgentOptimizer:
    """Optimizes agent selection for better performance and functionality."""
    
    # Agent categories and their conflicts
    AGENT_CATEGORIES = {
        'github': ['github_agent', 'github_security_agent'],
        'security': ['security_agent', 'snyk_scanner_agent', 'github_security_agent'],
        'chart': ['chart_agent'],
        'pdf': ['pdf_agent'],
        'scraper': ['scraper_agent'],
        'azure': ['azure_agent'],
        'sample': ['sample_agent']
    }
    
    # Priority within each category (lower = higher priority)
    AGENT_PRIORITIES = {
        'github_security_agent': 1,  # Combined GitHub + security
        'github_agent': 2,
        'chart_agent': 1,
        'pdf_agent': 1,
        'security_agent': 2,
        'snyk_scanner_agent': 3,  # Standalone security tool
        'scraper_agent': 1,
        'azure_agent': 1,
        'sample_agent': 3
    }
    
    # Recommended combinations for specific use cases
    TASK_SPECIFIC_RECOMMENDATIONS = {
        'github_security': ['github_security_agent'],  # Single agent is often better
        'dependabot': ['github_security_agent'],
        'codeql': ['github_security_agent'], 
        'github_issues': ['github_agent'],
        'github_prs': ['github_agent'],
        'charts_only': ['chart_agent'],
        'pdf_analysis': ['pdf_agent'],
        'web_security': ['security_agent'],
    }
    
    # Recommended combinations
    GOOD_COMBINATIONS = [
        ['github_agent', 'chart_agent'],
        ['github_security_agent', 'chart_agent'],
        ['pdf_agent', 'chart_agent'],
        ['scraper_agent', 'chart_agent'],
        ['github_agent', 'pdf_agent'],
        ['security_agent', 'pdf_agent'],
    ]
    
    # Problematic combinations
    BAD_COMBINATIONS = [
        ['github_agent', 'github_security_agent'],  # Redundant
        ['security_agent', 'snyk_scanner_agent'],   # Overlapping tools
        ['security_agent', 'github_security_agent'], # Overlapping security
    ]
    
    @classmethod
    def optimize_agent_selection(
        cls, 
        requested_agents: List[str], 
        available_agents: Dict[str, any],
        max_agents: int = 3
    ) -> Dict[str, any]:
        """
        Optimize agent selection for better performance.
        
        Returns:
            Dict with 'agents', 'warnings', and 'recommendations'
        """
        result = {
            'agents': [],
            'warnings': [],
            'recommendations': [],
            'original_count': len(requested_agents),
            'optimized_count': 0
        }
        
        # Filter out unavailable agents
        valid_agents = [a for a in requested_agents if a in available_agents]
        invalid_agents = [a for a in requested_agents if a not in available_agents]
        
        if invalid_agents:
            result['warnings'].append(f"Unavailable agents removed: {', '.join(invalid_agents)}")
        
        # Limit number of agents
        if len(valid_agents) > max_agents:
            result['warnings'].append(
                f"Too many agents requested ({len(valid_agents)}), limiting to {max_agents}"
            )
            
        # Detect conflicting agents
        conflicts = cls._detect_conflicts(valid_agents)
        if conflicts:
            result['warnings'].extend([f"Conflicting agents detected: {conflict}" for conflict in conflicts])
        
        # Optimize selection
        optimized_agents = cls._resolve_conflicts(valid_agents, max_agents)
        
        # Generate recommendations
        if len(optimized_agents) < len(valid_agents):
            removed = set(valid_agents) - set(optimized_agents)
            result['recommendations'].append(
                f"Removed conflicting agents: {', '.join(removed)}"
            )
        
        # Suggest improvements
        suggestions = cls._suggest_improvements(optimized_agents, available_agents)
        result['recommendations'].extend(suggestions)
        
        result['agents'] = optimized_agents
        result['optimized_count'] = len(optimized_agents)
        
        return result
    
    @classmethod
    def _detect_conflicts(cls, agents: List[str]) -> List[str]:
        """Detect conflicting agent combinations."""
        conflicts = []
        
        # Check for same-category conflicts
        categories_used = {}
        for agent in agents:
            for category, category_agents in cls.AGENT_CATEGORIES.items():
                if agent in category_agents:
                    if category in categories_used:
                        conflicts.append(f"{category}: {categories_used[category]} vs {agent}")
                    else:
                        categories_used[category] = agent
        
        # Check for known bad combinations
        agent_set = set(agents)
        for bad_combo in cls.BAD_COMBINATIONS:
            if all(agent in agent_set for agent in bad_combo):
                conflicts.append(f"Bad combination: {' + '.join(bad_combo)}")
        
        return conflicts
    
    @classmethod
    def _resolve_conflicts(cls, agents: List[str], max_agents: int) -> List[str]:
        """Resolve conflicts by selecting best agents from each category."""
        # Group agents by category
        categories = {}
        uncategorized = []
        
        for agent in agents:
            categorized = False
            for category, category_agents in cls.AGENT_CATEGORIES.items():
                if agent in category_agents:
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(agent)
                    categorized = True
                    break
            
            if not categorized:
                uncategorized.append(agent)
        
        # Select best agent from each category
        optimized = []
        
        for category, category_agents in categories.items():
            # Sort by priority (lower number = higher priority)
            best_agent = min(category_agents, key=lambda x: cls.AGENT_PRIORITIES.get(x, 99))
            optimized.append(best_agent)
        
        # Add uncategorized agents
        optimized.extend(uncategorized)
        
        # Limit to max_agents
        if len(optimized) > max_agents:
            # Sort all by priority and take top N
            optimized = sorted(optimized, key=lambda x: cls.AGENT_PRIORITIES.get(x, 99))[:max_agents]
        
        return optimized
    
    @classmethod
    def _suggest_improvements(cls, current_agents: List[str], available_agents: Dict[str, any]) -> List[str]:
        """Suggest improvements to current agent selection."""
        suggestions = []
        
        # Check for task-specific optimizations
        agent_set = set(current_agents)
        if len(current_agents) > 1:
            # Check if single agent would be better
            for task, recommended in cls.TASK_SPECIFIC_RECOMMENDATIONS.items():
                if (len(recommended) == 1 and 
                    recommended[0] in available_agents and
                    recommended[0] in agent_set):
                    other_agents = agent_set - set(recommended)
                    if other_agents:
                        suggestions.append(f"For {task} tasks, consider using only '{recommended[0]}' (currently using {len(current_agents)} agents)")
        
        # Suggest good combinations
        for good_combo in cls.GOOD_COMBINATIONS:
            if (len(good_combo) <= len(current_agents) and 
                all(agent in available_agents for agent in good_combo) and
                not any(agent in current_agents for agent in good_combo)):
                suggestions.append(f"Consider trying: {' + '.join(good_combo)}")
        
        # Suggest combined agents over separate ones
        if 'github_agent' in current_agents and 'security_agent' in current_agents:
            if 'github_security_agent' in available_agents:
                suggestions.append("Consider using 'github_security_agent' instead of separate GitHub and security agents")
        
        # Performance suggestions
        if len(current_agents) > 2:
            suggestions.append("For faster responses, try using fewer agents")
        
        if 'chart_agent' in current_agents:
            suggestions.append("Chart agent may timeout - ensure chart server is running properly")
        
        return suggestions


def get_agent_recommendations(
    requested_agents: List[str], 
    available_agents: Dict[str, any]
) -> Dict[str, any]:
    """Get optimized agent selection with recommendations."""
    return AgentOptimizer.optimize_agent_selection(requested_agents, available_agents)
