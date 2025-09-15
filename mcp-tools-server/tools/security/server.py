"""
Security assessment tools for the MCP Tools Server.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from shared.utils.logging import logger

from . import __version__
from .dns_analyzer import DNSSecurityAnalyzer
from .header_analyzer import SecurityHeaderAnalyzer
from .report_generator import SecurityReportGenerator
from .safe_scanner import SafeSecurityScanner
from .ssl_analyzer import SSLAnalyzer

# logger = setup_tool_logger('security')


def register_security_tools(mcp):
    """Register security assessment tools with the MCP server."""

    # Initialize all analyzers
    header_analyzer = SecurityHeaderAnalyzer()
    ssl_analyzer = SSLAnalyzer()
    dns_analyzer = DNSSecurityAnalyzer()
    safe_scanner = SafeSecurityScanner()
    report_generator = SecurityReportGenerator()

    @mcp.tool(
        name="security_analyze_headers",
        description="Analyze HTTP security headers for a website (safe, non-invasive check).",
    )
    async def analyze_security_headers(url: str) -> dict:
        """
        Analyze HTTP security headers for common vulnerabilities.

        Args:
            url: Target URL to analyze (e.g., https://example.com)

        Returns:
            Dictionary with security header analysis results
        """
        try:
            logger.info(f"Starting security header analysis for: {url}")
            start_time = time.time()

            # Validate URL format
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            result = await header_analyzer.analyze_headers(url)

            # Add performance metrics
            result["analysis_duration"] = round(time.time() - start_time, 2)
            result["tool_version"] = __version__

            logger.info(f"Security header analysis completed for: {url}")
            return result

        except Exception as e:
            logger.error(f"Error in security header analysis: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(
        name="security_analyze_ssl",
        description="Analyze SSL/TLS configuration and certificate details (safe, non-invasive check).",
    )
    async def analyze_ssl_configuration(domain: str, port: int = 443) -> dict:
        """
        Analyze SSL/TLS configuration for security issues.

        Args:
            domain: Domain to check (e.g., example.com)
            port: Port to check (default: 443)

        Returns:
            Dictionary with SSL/TLS analysis results
        """
        try:
            logger.info(f"Starting SSL analysis for: {domain}:{port}")
            start_time = time.time()

            # Clean domain (remove protocol if present)
            if domain.startswith(("http://", "https://")):
                parsed = urlparse(domain)
                domain = parsed.netloc or parsed.path

            result = await ssl_analyzer.analyze_ssl_config(domain, port)

            # Add performance metrics
            result["analysis_duration"] = round(time.time() - start_time, 2)
            result["tool_version"] = __version__

            logger.info(f"SSL analysis completed for: {domain}:{port}")
            return result

        except Exception as e:
            logger.error(f"Error in SSL analysis: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(
        name="security_analyze_dns",
        description="Analyze DNS security configuration including DNSSEC, email security, and CAA records.",
    )
    async def analyze_dns_security(
        domain: str, include_subdomains: bool = False, check_email_security: bool = True
    ) -> dict:
        """
        Analyze DNS security configuration.

        Args:
            domain: Domain to analyze (e.g., example.com)
            include_subdomains: Whether to check common subdomains
            check_email_security: Whether to check email security records

        Returns:
            Dictionary with DNS security analysis results
        """
        try:
            logger.info(f"Starting DNS security analysis for: {domain}")
            start_time = time.time()

            result = await dns_analyzer.analyze_dns_security(
                domain, include_subdomains, check_email_security
            )

            # Add performance metrics
            result["analysis_duration"] = round(time.time() - start_time, 2)
            result["tool_version"] = __version__

            logger.info(f"DNS security analysis completed for: {domain}")
            return result

        except Exception as e:
            logger.error(f"Error in DNS security analysis: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(
        name="security_quick_scan",
        description="Perform a quick security assessment combining headers and SSL analysis.",
    )
    async def quick_security_scan(url: str) -> dict:
        """
        Perform a comprehensive quick security scan.

        Args:
            url: Target URL to scan (e.g., https://example.com)

        Returns:
            Dictionary with combined security analysis results
        """
        try:
            logger.info(f"Starting quick security scan for: {url}")
            start_time = time.time()

            # Validate and normalize URL
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            # Run analyses concurrently
            header_task = header_analyzer.analyze_headers(url)
            ssl_task = ssl_analyzer.analyze_ssl_config(domain, 443)

            header_result, ssl_result = await asyncio.gather(
                header_task, ssl_task, return_exceptions=True
            )

            # Handle exceptions properly
            if isinstance(header_result, Exception):
                header_result = {"success": False, "error": str(header_result)}
            if isinstance(ssl_result, Exception):
                ssl_result = {"success": False, "error": str(ssl_result)}

            # Calculate overall security score
            overall_score = 0
            scores_count = 0

            # Only access dict methods if we have valid dictionaries
            if (
                isinstance(header_result, dict)
                and header_result.get("success")
                and "security_score" in header_result
            ):
                overall_score += header_result["security_score"]
                scores_count += 1

            if (
                isinstance(ssl_result, dict)
                and ssl_result.get("success")
                and "ssl_score" in ssl_result
            ):
                overall_score += ssl_result["ssl_score"]
                scores_count += 1

            overall_score = round(overall_score / scores_count, 1) if scores_count > 0 else 0

            # Combine recommendations
            all_recommendations = []
            if isinstance(header_result, dict) and header_result.get("recommendations"):
                all_recommendations.extend(header_result["recommendations"])
            if isinstance(ssl_result, dict) and ssl_result.get("recommendations"):
                all_recommendations.extend(ssl_result["recommendations"])

            result = {
                "success": True,
                "url": url,
                "domain": domain,
                "overall_security_score": overall_score,
                "overall_grade": _get_security_grade(overall_score),
                "header_analysis": header_result,
                "ssl_analysis": ssl_result,
                # Top 10 recommendations
                "combined_recommendations": all_recommendations[:10],
                "analysis_duration": round(time.time() - start_time, 2),
                "tool_version": __version__,
                "scan_timestamp": time.time(),
            }

            logger.info(f"Quick security scan completed for: {url}")
            return result

        except Exception as e:
            logger.error(f"Error in quick security scan: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(
        name="security_comprehensive_scan",
        description="Perform comprehensive security assessment using the safe scanner.",
    )
    async def comprehensive_security_scan(
        target: str,
        scan_profile: str = "standard",
        custom_options: Optional[Dict[str, bool]] = None,
    ) -> dict:
        """
        Perform comprehensive security scan on a target.

        Args:
            target: Target URL or domain to scan
            scan_profile: Scan profile ('quick', 'standard', 'comprehensive', 'compliance')
            custom_options: Custom scan options to override profile defaults

        Returns:
            Dictionary with comprehensive security analysis results
        """
        try:
            logger.info(f"Starting comprehensive security scan for: {target}")
            start_time = time.time()

            result = await safe_scanner.scan_target(target, scan_profile, custom_options)

            # Add performance metrics
            if isinstance(result, dict) and result.get("success") and "scan_metadata" in result:
                result["scan_metadata"]["total_duration"] = round(time.time() - start_time, 2)
                result["scan_metadata"]["tool_version"] = __version__

            logger.info(f"Comprehensive security scan completed for: {target}")
            return result

        except Exception as e:
            logger.error(f"Error in comprehensive security scan: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(
        name="security_batch_scan",
        description="Perform security scans on multiple targets concurrently.",
    )
    async def batch_security_scan(
        targets: List[str], scan_profile: str = "standard", max_concurrent: int = 5
    ) -> dict:
        """
        Perform security scans on multiple targets.

        Args:
            targets: List of targets to scan
            scan_profile: Scan profile to use for all targets
            max_concurrent: Maximum concurrent scans

        Returns:
            Dictionary with batch scan results
        """
        try:
            logger.info(f"Starting batch security scan for {len(targets)} targets")

            result = await safe_scanner.batch_scan_targets(targets, scan_profile, max_concurrent)

            logger.info("Batch security scan completed")
            return result

        except Exception as e:
            logger.error(f"Error in batch security scan: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(
        name="security_compare_targets", description="Compare security posture of multiple targets."
    )
    async def compare_security_targets(targets: List[str], scan_profile: str = "standard") -> dict:
        """
        Compare security posture of multiple targets.

        Args:
            targets: List of targets to compare
            scan_profile: Scan profile to use

        Returns:
            Dictionary with comparison analysis
        """
        try:
            logger.info(f"Starting security comparison for {len(targets)} targets")

            result = await safe_scanner.compare_targets(targets, scan_profile)

            logger.info("Security comparison completed")
            return result

        except Exception as e:
            logger.error(f"Error in security comparison: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(
        name="security_continuous_monitoring",
        description="Perform continuous monitoring scan with baseline comparison.",
    )
    async def continuous_monitoring_scan(target: str, monitoring_config: Dict[str, Any]) -> dict:
        """
        Perform continuous monitoring scan.

        Args:
            target: Target to monitor
            monitoring_config: Monitoring configuration including baseline and thresholds

        Returns:
            Dictionary with monitoring results and change detection
        """
        try:
            logger.info(f"Starting continuous monitoring for: {target}")

            result = await safe_scanner.continuous_monitoring_scan(target, monitoring_config)

            logger.info(f"Continuous monitoring completed for: {target}")
            return result

        except Exception as e:
            logger.error(f"Error in continuous monitoring: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(
        name="security_check_multiple_sites",
        description="Perform security header analysis on multiple websites concurrently.",
    )
    async def check_multiple_sites(urls: List[str], max_concurrent: int = 5) -> dict:
        """
        Analyze security headers for multiple websites.

        Args:
            urls: List of URLs to analyze
            max_concurrent: Maximum concurrent requests (default: 5)

        Returns:
            Dictionary with results for all URLs
        """
        try:
            logger.info(f"Starting multi-site security analysis for {len(urls)} URLs")
            start_time = time.time()

            # Validate URLs
            validated_urls = []
            for url in urls:
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                validated_urls.append(url)

            # Limit concurrent requests
            semaphore = asyncio.Semaphore(min(max_concurrent, 10))

            async def analyze_single_url(url):
                async with semaphore:
                    return await header_analyzer.analyze_headers(url)

            # Run analyses concurrently
            tasks = [analyze_single_url(url) for url in validated_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            processed_results = []
            successful_scans = 0

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(
                        {"url": validated_urls[i], "success": False, "error": str(result)}
                    )
                else:
                    processed_results.append(result)
                    if isinstance(result, dict) and result.get("success"):
                        successful_scans += 1

            # Calculate summary statistics
            security_scores = [
                r.get("security_score", 0)
                for r in processed_results
                if isinstance(r, dict) and r.get("success")
            ]
            avg_score = (
                round(sum(security_scores) / len(security_scores), 1) if security_scores else 0
            )

            return {
                "success": True,
                "total_sites": len(urls),
                "successful_scans": successful_scans,
                "failed_scans": len(urls) - successful_scans,
                "average_security_score": avg_score,
                "results": processed_results,
                "analysis_duration": round(time.time() - start_time, 2),
                "tool_version": __version__,
            }

        except Exception as e:
            logger.error(f"Error in multi-site security analysis: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(
        name="security_generate_report",
        description="Generate comprehensive security assessment report from analysis data.",
    )
    async def generate_security_report(
        security_data: dict,
        report_type: str = "technical",
        include_compliance: bool = False,
        compliance_framework: str = "owasp_top10",
    ) -> dict:
        """
        Generate security report from analysis data.

        Args:
            security_data: Security analysis results from various tools
            report_type: Type of report ('executive', 'technical', 'compliance', 'quick')
            include_compliance: Whether to include compliance mapping
            compliance_framework: Framework to map against ('owasp_top10', 'nist_cybersecurity')

        Returns:
            Dictionary with formatted security report
        """
        try:
            logger.info(f"Generating {report_type} security report")

            result = report_generator.generate_comprehensive_report(
                security_data,
                report_type,
                include_recommendations=True,
                include_compliance=include_compliance,
                compliance_framework=compliance_framework,
            )

            logger.info("Security report generation completed")
            return result

        except Exception as e:
            logger.error(f"Error generating security report: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(
        name="security_export_report",
        description="Export security report in different formats (JSON, Markdown, HTML).",
    )
    async def export_security_report(
        report_data: dict, export_formats: List[str] = ["json", "markdown"]
    ) -> dict:
        """
        Export security report in different formats.

        Args:
            report_data: Security report data to export
            export_formats: List of formats to export ('json', 'markdown', 'html')

        Returns:
            Dictionary with exported report formats
        """
        try:
            logger.info(f"Exporting security report in formats: {export_formats}")

            result = report_generator.export_report_formats(report_data, export_formats)

            logger.info("Security report export completed")
            return result

        except Exception as e:
            logger.error(f"Error exporting security report: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(
        name="security_generate_report_summary",
        description="Generate summary of multiple security reports.",
    )
    async def generate_report_summary(reports: List[Dict[str, Any]]) -> dict:
        """
        Generate summary of multiple security reports.

        Args:
            reports: List of security report results

        Returns:
            Dictionary with report summary statistics
        """
        try:
            logger.info(f"Generating summary for {len(reports)} reports")

            result = report_generator.generate_report_summary(reports)

            logger.info("Report summary generation completed")
            return result

        except Exception as e:
            logger.error(f"Error generating report summary: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(
        name="security_get_scan_profiles",
        description="Get available security scan profiles and their descriptions.",
    )
    async def get_security_scan_profiles() -> dict:
        """
        Get available scan profiles.

        Returns:
            Dictionary with available scan profiles and descriptions
        """
        try:
            profiles = safe_scanner.get_scan_profiles()

            return {
                "success": True,
                "scan_profiles": profiles,
                "default_profile": "standard",
                "tool_version": __version__,
            }

        except Exception as e:
            logger.error(f"Error getting scan profiles: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(
        name="security_validate_target",
        description="Validate that a target is accessible for security scanning.",
    )
    async def validate_security_target(target: str) -> dict:
        """
        Validate target accessibility.

        Args:
            target: Target to validate

        Returns:
            Dictionary with validation results
        """
        try:
            logger.info(f"Validating target: {target}")

            result = safe_scanner.validate_target_accessibility(target)

            return result

        except Exception as e:
            logger.error(f"Error validating target: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(
        name="security_tools_status", description="Check security tools status and capabilities."
    )
    async def security_tools_status() -> dict:
        """
        Get security tools status and capabilities.

        Returns:
            Dictionary with tools status and feature availability
        """
        try:
            return {
                "success": True,
                "tool_version": __version__,
                "available_tools": [
                    "security_analyze_headers",
                    "security_analyze_ssl",
                    "security_analyze_dns",
                    "security_quick_scan",
                    "security_comprehensive_scan",
                    "security_batch_scan",
                    "security_compare_targets",
                    "security_continuous_monitoring",
                    "security_check_multiple_sites",
                    "security_generate_report",
                    "security_export_report",
                    "security_generate_report_summary",
                    "security_get_scan_profiles",
                    "security_validate_target",
                ],
                "capabilities": {
                    "security_headers_analysis": True,
                    "ssl_tls_analysis": True,
                    "dns_security_analysis": True,
                    "comprehensive_scanning": True,
                    "batch_scanning": True,
                    "target_comparison": True,
                    "continuous_monitoring": True,
                    "multi_site_scanning": True,
                    "concurrent_analysis": True,
                    "report_generation": True,
                    "multiple_export_formats": True,
                    "compliance_mapping": True,
                },
                "supported_analyses": {
                    "http_security_headers": [
                        "Strict-Transport-Security (HSTS)",
                        "Content-Security-Policy (CSP)",
                        "X-Frame-Options",
                        "X-Content-Type-Options",
                        "Referrer-Policy",
                        "Permissions-Policy",
                        "X-XSS-Protection",
                    ],
                    "ssl_tls_checks": [
                        "Certificate validity",
                        "Certificate expiration",
                        "Signature algorithms",
                        "Protocol support",
                        "Subject Alternative Names",
                        "Certificate chain validation",
                    ],
                    "dns_security_checks": [
                        "DNSSEC validation",
                        "SPF records",
                        "DMARC policies",
                        "DKIM selectors",
                        "CAA records",
                        "Subdomain discovery",
                    ],
                },
                "scan_profiles": safe_scanner.get_scan_profiles(),
                "ethical_guidelines": {
                    "non_invasive": True,
                    "read_only": True,
                    "no_exploitation": True,
                    "educational_purpose": True,
                    "safe_scanning_only": True,
                },
                "phase": "Phase 1: Complete Safe Assessment Tools Suite",
            }

        except Exception as e:
            logger.error(f"Error getting security tools status: {e}")
            return {"success": False, "error": str(e)}


def _get_security_grade(score: float) -> str:
    """Convert security score to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


# Log successful registration
logger.info("Security assessment tools registered successfully")
