#!/usr/bin/env python3
"""
Snyk Scanner Usage Examples

This script demonstrates how to use the Snyk Scanner MCP tool for various security scanning scenarios.
"""

import asyncio
import json
import tempfile
from pathlib import Path

# Example usage functions for the Snyk Scanner MCP tool


async def example_check_snyk_installation():
    """Example: Check if Snyk CLI is installed and configured."""
    print("🔍 Example: Checking Snyk CLI Installation")
    print("=" * 50)
    
    # This would be called by the MCP client
    print("MCP Tool Call: snyk_check_installation()")
    
    # Expected response format
    example_response = {
        "success": True,
        "installation_status": {
            "installed": True,
            "version": "1.1296.2",
            "authenticated": True,
            "auth_details": "Authenticated",
            "config_org": "my-organization"
        },
        "tool_version": "1.0.0"
    }
    
    print("📋 Expected Response:")
    print(json.dumps(example_response, indent=2))
    print()


async def example_scan_local_project():
    """Example: Scan a local project directory."""
    print("🔍 Example: Scanning Local Project")
    print("=" * 50)
    
    project_path = "/home/user/my-project"
    
    print(f"MCP Tool Call: snyk_scan_project(")
    print(f"  project_path='{project_path}',")
    print(f"  severity_threshold='medium',")
    print(f"  include_dev_dependencies=True,")
    print(f"  timeout=300")
    print(f")")
    
    # Expected response format
    example_response = {
        "success": True,
        "scan_metadata": {
            "success": True,
            "project_path": project_path,
            "scan_type": "test",
            "execution_time": 45.2,
            "scan_timestamp": 1693827600.0,
            "formatted_timestamp": "2023-09-04T10:00:00",
            "snyk_version": "1.1296.2"
        },
        "summary": {
            "critical": 2,
            "high": 5,
            "medium": 12,
            "low": 8,
            "total": 27
        },
        "vulnerability_count": 27,
        "detailed_summary": {
            "total_vulnerabilities": 27,
            "by_severity": {"critical": 2, "high": 5, "medium": 12, "low": 8},
            "by_package_manager": {"npm": 20, "pip": 7},
            "patchable_count": 15,
            "upgradeable_count": 22,
            "most_critical": [
                {
                    "id": "SNYK-JS-LODASH-567746",
                    "title": "Prototype Pollution",
                    "severity": "critical",
                    "package": "lodash",
                    "cvss_score": 9.8
                }
            ]
        },
        "risk_assessment": {
            "risk_level": "high",
            "score": 75.3,
            "description": "High security risk with 2 critical vulnerabilities"
        },
        "project_info": {
            "path": project_path,
            "type": "node.js"
        },
        "tool_version": "1.0.0"
    }
    
    print("📋 Expected Response:")
    print(json.dumps(example_response, indent=2))
    print()


async def example_scan_github_repo():
    """Example: Scan a GitHub repository."""
    print("🔍 Example: Scanning GitHub Repository")
    print("=" * 50)
    
    repo_url = "https://github.com/microsoft/typescript"
    
    print(f"MCP Tool Call: snyk_scan_github_repo(")
    print(f"  repo_url='{repo_url}',")
    print(f"  severity_threshold='high',")
    print(f"  include_dev_dependencies=False,")
    print(f"  timeout=600")
    print(f")")
    
    # Expected response format
    example_response = {
        "success": True,
        "scan_metadata": {
            "success": True,
            "project_path": repo_url,
            "scan_type": "github_scan",
            "execution_time": 120.5,
            "scan_timestamp": 1693827600.0
        },
        "summary": {
            "critical": 0,
            "high": 2,
            "medium": 5,
            "low": 3,
            "total": 10
        },
        "vulnerability_count": 10,
        "repository_info": {
            "url": repo_url,
            "owner": "microsoft",
            "repository": "typescript"
        },
        "risk_assessment": {
            "risk_level": "medium",
            "score": 45.0,
            "description": "Medium security risk with 2 high-severity vulnerabilities"
        },
        "tool_version": "1.0.0"
    }
    
    print("📋 Expected Response:")
    print(json.dumps(example_response, indent=2))
    print()


async def example_batch_scan():
    """Example: Batch scan multiple targets."""
    print("🔍 Example: Batch Scanning Multiple Targets")
    print("=" * 50)
    
    targets = [
        "https://github.com/user/repo1",
        "/home/user/project1",
        "https://github.com/user/repo2"
    ]
    
    print(f"MCP Tool Call: snyk_batch_scan(")
    print(f"  targets={targets},")
    print(f"  scan_type='auto',")
    print(f"  severity_threshold='medium',")
    print(f"  max_concurrent=2,")
    print(f"  timeout_per_scan=300")
    print(f")")
    
    # Expected response format
    example_response = {
        "success": True,
        "batch_summary": {
            "total_targets": 3,
            "successful_scans": 2,
            "failed_scans": 1,
            "total_vulnerabilities": 45
        },
        "executive_summary": {
            "executive_summary": {
                "total_projects_scanned": 3,
                "successful_scans": 2,
                "failed_scans": 1,
                "total_vulnerabilities": 45,
                "overall_risk_level": "high"
            }
        },
        "individual_results": [
            # Individual scan results for each target
        ],
        "failed_targets": [
            {
                "target": "/home/user/project1",
                "error": "Path not accessible"
            }
        ],
        "tool_version": "1.0.0"
    }
    
    print("📋 Expected Response:")
    print(json.dumps(example_response, indent=2))
    print()


async def example_api_usage():
    """Example: Using the API endpoint for GitHub security scanning."""
    print("🔍 Example: API Endpoint for GitHub Security Scanning")
    print("=" * 50)
    
    print("HTTP POST /agents/scan-github-security")
    print("Headers:")
    print("  Authorization: Bearer <your-jwt-token>")
    print("  Content-Type: application/x-www-form-urlencoded")
    print()
    print("Form Data:")
    print("  github_url: https://github.com/vulnerable/project")
    print("  severity_threshold: medium")
    print("  include_dev_deps: true")
    print("  chat_id: optional-chat-id")
    print()
    
    example_api_response = {
        "id": "query-123",
        "message": "Security scan of https://github.com/vulnerable/project",
        "response": "# Security Scan Report\\n\\n## Repository: vulnerable/project\\n\\n### Summary\\n- Total vulnerabilities: 15\\n- Critical: 1\\n- High: 4\\n- Medium: 7\\n- Low: 3\\n\\n### Critical Vulnerabilities\\n1. **Prototype Pollution in lodash@4.17.20**\\n   - CVE-2020-8203\\n   - CVSS Score: 9.8\\n   - Fix: Upgrade to lodash@4.17.21\\n\\n### Recommendations\\n- Upgrade all vulnerable packages immediately\\n- Enable Snyk monitoring for continuous security\\n- Review dependency management practices",
        "agent_used": "github_security_agent",
        "status": "completed",
        "created_at": "2023-09-04T10:00:00",
        "token_usage": {
            "total_tokens": 1250,
            "prompt_tokens": 850,
            "completion_tokens": 400
        },
        "metadata": {
            "scan_type": "github_security",
            "repository_url": "https://github.com/vulnerable/project",
            "severity_threshold": "medium",
            "include_dev_deps": True
        }
    }
    
    print("📋 Expected API Response:")
    print(json.dumps(example_api_response, indent=2))
    print()


async def example_user_workflow():
    """Example: Complete user workflow from login to scan results."""
    print("🔍 Example: Complete User Workflow")
    print("=" * 50)
    
    workflow_steps = [
        {
            "step": 1,
            "action": "User Login",
            "description": "User authenticates with the agent-hub-api",
            "endpoint": "POST /auth/login",
            "result": "JWT token obtained"
        },
        {
            "step": 2,
            "action": "Check Available Agents",
            "description": "User queries available agents including GitHub and Snyk capabilities",
            "endpoint": "GET /agents/available",
            "result": "List includes 'github_security_agent' and 'snyk_scanner_agent'"
        },
        {
            "step": 3,
            "action": "Submit Security Scan Request",
            "description": "User provides GitHub repository URL for security scanning",
            "endpoint": "POST /agents/scan-github-security",
            "payload": {
                "github_url": "https://github.com/example/repo",
                "severity_threshold": "medium",
                "include_dev_deps": True
            }
        },
        {
            "step": 4,
            "action": "System Processing",
            "description": "System clones repository and runs Snyk vulnerability scan",
            "internal_calls": [
                "GitHub clone operation",
                "Snyk CLI execution",
                "Results parsing and analysis"
            ]
        },
        {
            "step": 5,
            "action": "Receive Results",
            "description": "User receives comprehensive security report",
            "response_includes": [
                "Vulnerability counts by severity",
                "Detailed vulnerability information",
                "Remediation recommendations",
                "Risk assessment",
                "Executive summary"
            ]
        }
    ]
    
    print("📋 Complete Workflow Steps:")
    for step in workflow_steps:
        print(f"Step {step['step']}: {step['action']}")
        print(f"  Description: {step['description']}")
        if 'endpoint' in step:
            print(f"  Endpoint: {step['endpoint']}")
        if 'payload' in step:
            print(f"  Payload: {json.dumps(step['payload'], indent=4)}")
        if 'result' in step:
            print(f"  Result: {step['result']}")
        if 'internal_calls' in step:
            print(f"  Internal Operations: {', '.join(step['internal_calls'])}")
        if 'response_includes' in step:
            print(f"  Response Includes: {', '.join(step['response_includes'])}")
        print()


async def main():
    """Run all example demonstrations."""
    print("🚀 Snyk Scanner MCP Tool - Usage Examples")
    print("=" * 70)
    print()
    
    examples = [
        example_check_snyk_installation,
        example_scan_local_project,
        example_scan_github_repo,
        example_batch_scan,
        example_api_usage,
        example_user_workflow
    ]
    
    for example in examples:
        await example()
        print("\n" + "─" * 70 + "\n")
    
    print("✅ All examples completed!")
    print("\n💡 Next Steps:")
    print("1. Ensure Snyk CLI is installed and authenticated")
    print("2. Configure the MCP tools server with Snyk scanner")
    print("3. Start the agent-hub-api with the new endpoints")
    print("4. Test the security scanning workflow with a real repository")


if __name__ == "__main__":
    asyncio.run(main())
