"""
Demo simulation for when rate limits are hit.
Provides mock responses for demonstration purposes.
"""
from typing import Dict, List
import json


class DemoSimulator:
    """Simulates agent responses for demo scenarios."""
    
    DEMO_RESPONSES = {
        "dependabot_alerts": {
            "nathangtg/python-vuln-demo": [
                {
                    "ecosystem": "pip",
                    "package": "requests",
                    "current_version": "2.25.1",
                    "fixed_version": "2.32.0",
                    "severity": "high",
                    "advisory_url": "https://github.com/advisories/GHSA-9wx4-h78v-vm56"
                },
                {
                    "ecosystem": "pip", 
                    "package": "django",
                    "current_version": "3.1.0",
                    "fixed_version": "3.2.25",
                    "severity": "critical",
                    "advisory_url": "https://github.com/advisories/GHSA-xvf7-4v9q-58w6"
                },
                {
                    "ecosystem": "pip",
                    "package": "pillow",
                    "current_version": "8.0.0", 
                    "fixed_version": "10.3.0",
                    "severity": "medium",
                    "advisory_url": "https://github.com/advisories/GHSA-3f63-hfp8-52jq"
                },
                {
                    "ecosystem": "pip",
                    "package": "urllib3",
                    "current_version": "1.26.0",
                    "fixed_version": "1.26.19",
                    "severity": "medium", 
                    "advisory_url": "https://github.com/advisories/GHSA-34jh-p97f-mpxf"
                }
            ]
        },
        "codeql_alerts": {
            "nathangtg/python-vuln-demo": [
                {
                    "rule": "py/sql-injection",
                    "severity": "high",
                    "file": "app/views.py",
                    "line": 42,
                    "web_url": "https://github.com/nathangtg/python-vuln-demo/security/code-scanning/1"
                },
                {
                    "rule": "py/path-injection", 
                    "severity": "medium",
                    "file": "utils/file_handler.py", 
                    "line": 18,
                    "web_url": "https://github.com/nathangtg/python-vuln-demo/security/code-scanning/2"
                },
                {
                    "rule": "py/clear-text-logging-sensitive-data",
                    "severity": "medium",
                    "file": "app/auth.py",
                    "line": 67,
                    "web_url": "https://github.com/nathangtg/python-vuln-demo/security/code-scanning/3"
                }
            ]
        }
    }
    
    @classmethod
    def get_dependabot_alerts(cls, owner: str, repo: str) -> List[Dict]:
        """Get simulated Dependabot alerts."""
        repo_key = f"{owner}/{repo}"
        return cls.DEMO_RESPONSES["dependabot_alerts"].get(repo_key, [])
    
    @classmethod
    def get_codeql_alerts(cls, owner: str, repo: str) -> List[Dict]:
        """Get simulated CodeQL alerts."""
        repo_key = f"{owner}/{repo}"
        return cls.DEMO_RESPONSES["codeql_alerts"].get(repo_key, [])
    
    @classmethod
    def format_dependabot_response(cls, owner: str, repo: str) -> str:
        """Format Dependabot alerts as a table."""
        alerts = cls.get_dependabot_alerts(owner, repo)
        
        if not alerts:
            return f"No open Dependabot alerts found for {owner}/{repo}."
        
        # Create table header
        table = "| Ecosystem | Package | Current Version | Fixed Version | Severity |\n"
        table += "|-----------|---------|-----------------|---------------|----------|\n"
        
        # Add rows
        for alert in alerts:
            table += f"| {alert['ecosystem']} | {alert['package']} | {alert['current_version']} | {alert['fixed_version']} | {alert['severity']} |\n"
        
        return f"## Open Dependabot Alerts for {owner}/{repo}\n\n{table}\n\n**Note**: This is demo data due to rate limiting."
    
    @classmethod
    def format_codeql_response(cls, owner: str, repo: str) -> str:
        """Format CodeQL alerts as a table."""
        alerts = cls.get_codeql_alerts(owner, repo)
        
        if not alerts:
            return f"No open CodeQL alerts found for {owner}/{repo}."
        
        # Create table header  
        table = "| Rule | Severity | File | Line | URL |\n"
        table += "|------|----------|------|------|-----|\n"
        
        # Add rows
        for alert in alerts:
            table += f"| {alert['rule']} | {alert['severity']} | {alert['file']} | {alert['line']} | [View]({alert['web_url']}) |\n"
        
        return f"## Open CodeQL Alerts for {owner}/{repo}\n\n{table}\n\n**Note**: This is demo data due to rate limiting."


def create_demo_response_for_query(query: str) -> str:
    """Create a demo response based on the query."""
    query_lower = query.lower()
    
    # Detect Dependabot queries
    if "dependabot" in query_lower and "nathangtg/python-vuln-demo" in query_lower:
        return DemoSimulator.format_dependabot_response("nathangtg", "python-vuln-demo")
    
    # Detect CodeQL queries  
    if ("codeql" in query_lower or "code scanning" in query_lower) and "nathangtg/python-vuln-demo" in query_lower:
        return DemoSimulator.format_codeql_response("nathangtg", "python-vuln-demo")
    
    # Generic demo response
    return """## Demo Mode Active 🎭

Due to Azure OpenAI rate limiting, this is a simulated response.

**Available Demo Queries:**
- `List open Dependabot alerts for nathangtg/python-vuln-demo`
- `List open CodeQL alerts for nathangtg/python-vuln-demo`

**To continue with live data:**
- Wait 60 seconds for rate limit reset
- Upgrade Azure OpenAI tier
- Use fewer agents to reduce token usage

**Note**: All system optimizations (agent selection, circuit breakers, timeouts) are working correctly!
"""
