"""
Snyk Scanner MCP Tools Server

This module defines MCP tools for Snyk security scanning functionality.
"""

import json
import tempfile
import atexit
import signal
import asyncio
from typing import Any, Dict, List, Optional

from shared.utils.logging import logger

from .services.snyk_service import SnykConfig, SnykService
from .utils.path_validator import (
    clean_path,
    extract_repo_info,
    get_project_type,
    is_project_directory,
    is_valid_github_url,
    is_valid_path,
    normalize_path,
)
from .utils.output_formatter import (
    create_executive_summary,
    format_scan_report,
    format_vulnerability_details,
    format_vulnerability_summary,
    generate_recommendations,
    generate_risk_assessment,
)

__version__ = "1.0.0"

# Global service instance
_snyk_service: Optional[SnykService] = None


async def cleanup_snyk_service():
    """Clean up the global Snyk service instance."""
    global _snyk_service
    if _snyk_service:
        try:
            await _snyk_service.cleanup()
            logger.info("Snyk service cleanup completed")
        except Exception as e:
            logger.error(f"Error during Snyk service cleanup: {e}")
        finally:
            _snyk_service = None


def setup_cleanup_handlers():
    """Set up cleanup handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating cleanup...")
        asyncio.create_task(cleanup_snyk_service())
    
    # Register cleanup on exit
    atexit.register(lambda: asyncio.run(cleanup_snyk_service()) if _snyk_service else None)
    
    # Handle SIGTERM and SIGINT
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def get_snyk_service(config: Optional[Dict[str, Any]] = None) -> SnykService:
    """Get or create a Snyk service instance."""
    global _snyk_service

    if _snyk_service is None:
        # Setup cleanup handlers on first initialization
        setup_cleanup_handlers()
        
        snyk_config = SnykConfig()

        if config:
            # Apply configuration if provided
            if "timeout" in config:
                snyk_config.timeout = config["timeout"]
            if "severity_threshold" in config:
                snyk_config.severity_threshold = config["severity_threshold"]
            if "include_dev_dependencies" in config:
                snyk_config.include_dev_dependencies = config["include_dev_dependencies"]
            if "org" in config:
                snyk_config.org = config["org"]

        _snyk_service = SnykService(snyk_config)

    return _snyk_service


def register_snyk_scanner_tools(mcp):
    """
    Register Snyk scanner tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool(
        name="snyk_check_installation",
        description="Check if Snyk CLI is installed and properly configured.",
    )
    async def check_snyk_installation() -> str:
        """Check Snyk CLI installation and authentication status."""
        try:
            service = await get_snyk_service()
            result = await service.check_snyk_installation()
            
            return json.dumps({
                "success": True,
                "installation_status": result,
                "tool_version": __version__
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error checking Snyk installation: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "tool_version": __version__
            }, indent=2)

    @mcp.tool(
        name="snyk_scan_project",
        description="Scan a local project directory for security vulnerabilities using Snyk.",
    )
    async def scan_project(
        project_path: str,
        severity_threshold: str = "low",
        include_dev_dependencies: bool = True,
        timeout: int = 300
    ) -> str:
        """
        Scan a project directory for vulnerabilities.
        
        Args:
            project_path: Path to the project directory to scan
            severity_threshold: Minimum severity to report (low, medium, high, critical)
            include_dev_dependencies: Whether to include dev dependencies in scan
            timeout: Scan timeout in seconds
        """
        try:
            # Clean and validate path
            cleaned_path = clean_path(project_path)
            if not is_valid_path(cleaned_path):
                return json.dumps({
                    "success": False,
                    "error": f"Invalid or inaccessible path: {project_path}",
                    "tool_version": __version__
                }, indent=2)
            
            normalized_path = normalize_path(cleaned_path)
            
            if not is_project_directory(normalized_path):
                return json.dumps({
                    "success": False,
                    "error": f"Directory does not appear to contain a scannable project: {normalized_path}",
                    "project_type": get_project_type(normalized_path),
                    "tool_version": __version__
                }, indent=2)
            
            # Configure service
            config = {
                "severity_threshold": severity_threshold,
                "include_dev_dependencies": include_dev_dependencies,
                "timeout": timeout
            }
            service = await get_snyk_service(config)
            
            # Perform scan
            logger.info(f"Starting Snyk scan for project: {normalized_path}")
            scan_result = await service.scan_project(normalized_path, "test")
            
            # Format results
            formatted_report = format_scan_report(scan_result)
            formatted_report["project_info"] = {
                "path": normalized_path,
                "type": get_project_type(normalized_path)
            }
            formatted_report["tool_version"] = __version__
            
            logger.info(f"Snyk scan completed. Found {len(scan_result.vulnerabilities)} vulnerabilities")
            
            return json.dumps(formatted_report, indent=2)
            
        except Exception as e:
            logger.error(f"Error scanning project {project_path}: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "tool_version": __version__
            }, indent=2)

    @mcp.tool(
        name="snyk_scan_github_repo",
        description="Clone and scan a GitHub repository for security vulnerabilities.",
    )
    async def scan_github_repository(
        repo_url: str,
        severity_threshold: str = "low",
        include_dev_dependencies: bool = True,
        timeout: int = 600
    ) -> str:
        """
        Clone and scan a GitHub repository with timeout and session management.
        
        Args:
            repo_url: GitHub repository URL (e.g., https://github.com/owner/repo)
            severity_threshold: Minimum severity to report (low, medium, high, critical)
            include_dev_dependencies: Whether to include dev dependencies in scan
            timeout: Total timeout including clone and scan in seconds
        """
        try:
            # Validate GitHub URL
            if not is_valid_github_url(repo_url):
                return json.dumps({
                    "success": False,
                    "error": f"Invalid GitHub repository URL: {repo_url}",
                    "tool_version": __version__
                }, indent=2)
            
            repo_info = extract_repo_info(repo_url)
            if not repo_info:
                return json.dumps({
                    "success": False,
                    "error": f"Could not extract repository information from URL: {repo_url}",
                    "tool_version": __version__
                }, indent=2)
            
            owner, repo = repo_info
            
            # Configure service with longer timeout for GitHub operations
            config = {
                "severity_threshold": severity_threshold,
                "include_dev_dependencies": include_dev_dependencies,
                "timeout": min(timeout, 900)  # Cap at 15 minutes
            }
            service = await get_snyk_service(config)
            
            # Perform scan with timeout
            logger.info(f"Starting GitHub repository scan: {owner}/{repo}")
            
            try:
                scan_result = await asyncio.wait_for(
                    service.scan_github_repository(repo_url),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"GitHub scan timed out after {timeout} seconds")
                # Ensure cleanup happens
                await service.cleanup()
                return json.dumps({
                    "success": False,
                    "error": f"Scan operation timed out after {timeout} seconds",
                    "tool_version": __version__
                }, indent=2)
            
            # Format results
            formatted_report = format_scan_report(scan_result)
            formatted_report["repository_info"] = {
                "url": repo_url,
                "owner": owner,
                "repository": repo
            }
            formatted_report["tool_version"] = __version__
            
            logger.info(f"GitHub scan completed. Found {len(scan_result.vulnerabilities)} vulnerabilities")
            
            return json.dumps(formatted_report, indent=2)
            
        except Exception as e:
            logger.error(f"Error scanning GitHub repository {repo_url}: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "tool_version": __version__
            }, indent=2)

    @mcp.tool(
        name="snyk_scan_code_analysis",
        description="Perform static code analysis using Snyk Code.",
    )
    async def scan_code_analysis(
        project_path: str,
        timeout: int = 300
    ) -> str:
        """
        Perform static code analysis on a project.
        
        Args:
            project_path: Path to the project directory to analyze
            timeout: Analysis timeout in seconds
        """
        try:
            # Clean and validate path
            cleaned_path = clean_path(project_path)
            if not is_valid_path(cleaned_path):
                return json.dumps({
                    "success": False,
                    "error": f"Invalid or inaccessible path: {project_path}",
                    "tool_version": __version__
                }, indent=2)
            
            normalized_path = normalize_path(cleaned_path)
            
            # Configure service
            config = {"timeout": timeout}
            service = await get_snyk_service(config)
            
            # Perform code analysis
            logger.info(f"Starting Snyk Code analysis for: {normalized_path}")
            scan_result = await service.scan_code_analysis(normalized_path)
            
            # Format results
            formatted_report = format_scan_report(scan_result)
            formatted_report["project_info"] = {
                "path": normalized_path,
                "type": get_project_type(normalized_path)
            }
            formatted_report["tool_version"] = __version__
            
            logger.info(f"Code analysis completed. Found {len(scan_result.vulnerabilities)} issues")
            
            return json.dumps(formatted_report, indent=2)
            
        except Exception as e:
            logger.error(f"Error performing code analysis on {project_path}: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "tool_version": __version__
            }, indent=2)

    @mcp.tool(
        name="snyk_monitor_project",
        description="Set up continuous monitoring for a project with Snyk.",
    )
    async def monitor_project(
        project_path: str,
        org: Optional[str] = None,
        timeout: int = 120
    ) -> str:
        """
        Set up monitoring for a project.
        
        Args:
            project_path: Path to the project directory to monitor
            org: Snyk organization to use for monitoring
            timeout: Monitor setup timeout in seconds
        """
        try:
            # Clean and validate path
            cleaned_path = clean_path(project_path)
            if not is_valid_path(cleaned_path):
                return json.dumps({
                    "success": False,
                    "error": f"Invalid or inaccessible path: {project_path}",
                    "tool_version": __version__
                }, indent=2)
            
            normalized_path = normalize_path(cleaned_path)
            
            # Configure service
            config = {"timeout": timeout}
            if org:
                config["org"] = org
                
            service = await get_snyk_service(config)
            
            # Set up monitoring
            logger.info(f"Setting up Snyk monitoring for: {normalized_path}")
            scan_result = await service.scan_project(normalized_path, "monitor")
            
            # Format results
            formatted_report = format_scan_report(scan_result)
            formatted_report["project_info"] = {
                "path": normalized_path,
                "type": get_project_type(normalized_path)
            }
            formatted_report["tool_version"] = __version__
            
            return json.dumps(formatted_report, indent=2)
            
        except Exception as e:
            logger.error(f"Error setting up monitoring for {project_path}: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "tool_version": __version__
            }, indent=2)

    @mcp.tool(
        name="snyk_vulnerability_details",
        description="Get detailed information about a specific vulnerability.",
    )
    async def get_vulnerability_details(
        vulnerability_id: str
    ) -> str:
        """
        Get detailed information about a specific vulnerability.
        
        Args:
            vulnerability_id: Snyk vulnerability ID
        """
        try:
            # This would typically query Snyk's API for vulnerability details
            # For now, return a placeholder response
            return json.dumps({
                "success": True,
                "vulnerability_id": vulnerability_id,
                "message": "Vulnerability details endpoint not yet implemented",
                "note": "Use snyk_scan_project to get vulnerability information in scan results",
                "tool_version": __version__
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error getting vulnerability details for {vulnerability_id}: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "tool_version": __version__
            }, indent=2)

    @mcp.tool(
        name="snyk_batch_scan",
        description="Scan multiple projects or repositories in batch.",
    )
    async def batch_scan(
        targets: List[str],
        scan_type: str = "auto",
        severity_threshold: str = "low",
        max_concurrent: int = 3,
        timeout_per_scan: int = 300
    ) -> str:
        """
        Scan multiple targets in batch.
        
        Args:
            targets: List of project paths or GitHub URLs to scan
            scan_type: Type of scan ('auto', 'project', 'github')
            severity_threshold: Minimum severity to report
            max_concurrent: Maximum concurrent scans
            timeout_per_scan: Timeout per individual scan
        """
        try:
            import asyncio
            
            config = {
                "severity_threshold": severity_threshold,
                "timeout": timeout_per_scan
            }
            service = await get_snyk_service(config)
            
            # Create semaphore to limit concurrent scans
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def scan_single_target(target: str):
                async with semaphore:
                    try:
                        if scan_type == "auto":
                            # Auto-detect target type
                            if is_valid_github_url(target):
                                return await service.scan_github_repository(target)
                            else:
                                return await service.scan_project(target, "test")
                        elif scan_type == "github":
                            return await service.scan_github_repository(target)
                        else:  # project
                            return await service.scan_project(target, "test")
                    except Exception as e:
                        logger.error(f"Error scanning target {target}: {e}")
                        from .services.snyk_service import SnykScanResult
                        return SnykScanResult(
                            success=False,
                            project_path=target,
                            scan_type="batch_scan",
                            vulnerabilities=[],
                            summary={},
                            error=str(e)
                        )
            
            # Run scans concurrently
            logger.info(f"Starting batch scan of {len(targets)} targets")
            scan_results = await asyncio.gather(*[scan_single_target(target) for target in targets])
            
            # Create summary report
            successful_scans = [r for r in scan_results if r.success]
            failed_scans = [r for r in scan_results if not r.success]
            
            total_vulnerabilities = sum(len(r.vulnerabilities) for r in successful_scans)
            
            # Generate executive summary
            exec_summary = create_executive_summary(scan_results)
            
            batch_report = {
                "success": True,
                "batch_summary": {
                    "total_targets": len(targets),
                    "successful_scans": len(successful_scans),
                    "failed_scans": len(failed_scans),
                    "total_vulnerabilities": total_vulnerabilities
                },
                "executive_summary": exec_summary,
                "individual_results": [
                    format_scan_report(result) for result in scan_results
                ],
                "failed_targets": [
                    {"target": r.project_path, "error": r.error}
                    for r in failed_scans
                ],
                "tool_version": __version__
            }
            
            logger.info(f"Batch scan completed. {len(successful_scans)}/{len(targets)} successful")
            
            return json.dumps(batch_report, indent=2)
            
        except Exception as e:
            logger.error(f"Error in batch scan: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "tool_version": __version__
            }, indent=2)

    @mcp.tool(
        name="snyk_scanner_status",
        description="Check Snyk scanner tool status and capabilities.",
    )
    async def scanner_status() -> str:
        """Check the status and capabilities of the Snyk scanner tool."""
        try:
            service = await get_snyk_service()
            installation_status = await service.check_snyk_installation()
            snyk_version = await service.get_snyk_version()
            
            status_report = {
                "service_name": "Snyk Security Scanner",
                "tool_version": __version__,
                "status": "operational" if installation_status.get("installed") else "limited",
                "snyk_cli": installation_status,
                "capabilities": {
                    "dependency_scanning": True,
                    "code_analysis": True,
                    "github_repository_scanning": True,
                    "batch_scanning": True,
                    "continuous_monitoring": True,
                    "vulnerability_remediation": True,
                    "risk_assessment": True
                },
                "supported_package_managers": [
                    "npm", "yarn", "pip", "pipenv", "poetry",
                    "gem", "maven", "gradle", "go mod", "composer",
                    "nuget", "cargo", "pub"
                ],
                "supported_languages": [
                    "JavaScript/TypeScript", "Python", "Ruby", "Java/Kotlin",
                    "Go", "PHP", "C#/.NET", "Rust", "Dart/Flutter"
                ],
                "scan_types": {
                    "dependency_vulnerabilities": {
                        "description": "Scan for known vulnerabilities in dependencies",
                        "command": "snyk test"
                    },
                    "static_code_analysis": {
                        "description": "Static analysis for security issues in code",
                        "command": "snyk code test"
                    },
                    "continuous_monitoring": {
                        "description": "Set up ongoing monitoring",
                        "command": "snyk monitor"
                    }
                },
                "configuration": {
                    "authenticated": installation_status.get("authenticated", False),
                    "organization": installation_status.get("config_org"),
                    "severity_levels": ["low", "medium", "high", "critical"]
                }
            }
            
            return json.dumps(status_report, indent=2)
            
        except Exception as e:
            logger.error(f"Error checking scanner status: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "tool_version": __version__
            }, indent=2)

    logger.info("Snyk Scanner MCP tools registered")


def register_tools(mcp):
    """Register all Snyk scanner tools - alias for compatibility."""
    register_snyk_scanner_tools(mcp)
