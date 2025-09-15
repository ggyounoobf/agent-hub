"""
Output Formatter Utilities

Utilities for formatting Snyk scan results and generating summaries.
"""

from typing import Any, Dict, List
from datetime import datetime

from shared.utils.logging import logger


def format_vulnerability_summary(vulnerabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Format vulnerabilities into a structured summary.
    
    Args:
        vulnerabilities: List of vulnerability data.
        
    Returns:
        Formatted summary with counts and categorized issues.
    """
    summary = {
        "total_vulnerabilities": len(vulnerabilities),
        "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "by_type": {},
        "by_package_manager": {},
        "patchable_count": 0,
        "upgradeable_count": 0,
        "most_critical": [],
        "packages_affected": set(),
        "languages_affected": set()
    }
    
    try:
        for vuln in vulnerabilities:
            # Count by severity
            severity = vuln.get("severity", "unknown").lower()
            if severity in summary["by_severity"]:
                summary["by_severity"][severity] += 1
            
            # Count by type
            vuln_type = vuln.get("type", "unknown")
            summary["by_type"][vuln_type] = summary["by_type"].get(vuln_type, 0) + 1
            
            # Count by package manager
            pkg_manager = vuln.get("package_manager", "unknown")
            summary["by_package_manager"][pkg_manager] = summary["by_package_manager"].get(pkg_manager, 0) + 1
            
            # Count patchable/upgradeable
            if vuln.get("is_patchable", False):
                summary["patchable_count"] += 1
            if vuln.get("is_upgradeable", False):
                summary["upgradeable_count"] += 1
            
            # Track affected packages and languages
            if vuln.get("package"):
                summary["packages_affected"].add(vuln["package"])
            if vuln.get("language"):
                summary["languages_affected"].add(vuln["language"])
            
            # Collect most critical vulnerabilities (critical and high severity)
            if severity in ["critical", "high"] and len(summary["most_critical"]) < 10:
                summary["most_critical"].append({
                    "id": vuln.get("id"),
                    "title": vuln.get("title"),
                    "severity": severity,
                    "package": vuln.get("package"),
                    "cvss_score": vuln.get("cvss_score", 0)
                })
        
        # Convert sets to lists for JSON serialization
        summary["packages_affected"] = list(summary["packages_affected"])
        summary["languages_affected"] = list(summary["languages_affected"])
        
        # Sort most critical by CVSS score
        summary["most_critical"].sort(key=lambda x: x.get("cvss_score", 0), reverse=True)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error formatting vulnerability summary: {e}")
        return {"error": str(e)}


def format_scan_report(scan_result: "SnykScanResult") -> Dict[str, Any]:
    """
    Format a complete scan result into a comprehensive report.
    
    Args:
        scan_result: SnykScanResult object.
        
    Returns:
        Formatted report dictionary.
    """
    try:
        report = {
            "scan_metadata": {
                "success": scan_result.success,
                "project_path": scan_result.project_path,
                "scan_type": scan_result.scan_type,
                "execution_time": scan_result.execution_time,
                "scan_timestamp": scan_result.scan_timestamp,
                "formatted_timestamp": datetime.fromtimestamp(scan_result.scan_timestamp).isoformat() if scan_result.scan_timestamp else None,
                "snyk_version": scan_result.snyk_version
            },
            "summary": scan_result.summary,
            "vulnerability_count": len(scan_result.vulnerabilities),
            "error": scan_result.error
        }
        
        if scan_result.vulnerabilities:
            # Add detailed vulnerability summary
            vuln_summary = format_vulnerability_summary(scan_result.vulnerabilities)
            report["detailed_summary"] = vuln_summary
            
            # Add risk assessment
            report["risk_assessment"] = generate_risk_assessment(scan_result.vulnerabilities)
            
            # Add recommendations
            report["recommendations"] = generate_recommendations(scan_result.vulnerabilities)
        
        return report
        
    except Exception as e:
        logger.error(f"Error formatting scan report: {e}")
        return {"error": str(e)}


def generate_risk_assessment(vulnerabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a risk assessment based on vulnerabilities found.
    
    Args:
        vulnerabilities: List of vulnerability data.
        
    Returns:
        Risk assessment dictionary.
    """
    try:
        total_vulns = len(vulnerabilities)
        if total_vulns == 0:
            return {
                "risk_level": "low",
                "score": 0,
                "description": "No vulnerabilities found"
            }
        
        # Calculate risk score based on severity distribution
        severity_weights = {"critical": 10, "high": 7, "medium": 4, "low": 1}
        risk_score = 0
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "low").lower()
            if severity in severity_weights:
                risk_score += severity_weights[severity]
                severity_counts[severity] += 1
        
        # Normalize score (0-100 scale)
        max_possible_score = total_vulns * 10  # All critical
        normalized_score = min(100, (risk_score / max_possible_score) * 100) if max_possible_score > 0 else 0
        
        # Determine risk level
        if normalized_score >= 80 or severity_counts["critical"] > 0:
            risk_level = "critical"
        elif normalized_score >= 60 or severity_counts["high"] > 5:
            risk_level = "high"
        elif normalized_score >= 30 or severity_counts["medium"] > 10:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Generate description
        descriptions = {
            "critical": f"Critical security risk detected with {severity_counts['critical']} critical vulnerabilities",
            "high": f"High security risk with {severity_counts['high']} high-severity vulnerabilities",
            "medium": f"Medium security risk with {severity_counts['medium']} medium-severity vulnerabilities",
            "low": f"Low security risk with mainly low-severity vulnerabilities"
        }
        
        return {
            "risk_level": risk_level,
            "score": round(normalized_score, 1),
            "description": descriptions[risk_level],
            "severity_breakdown": severity_counts,
            "total_vulnerabilities": total_vulns
        }
        
    except Exception as e:
        logger.error(f"Error generating risk assessment: {e}")
        return {"error": str(e)}


def generate_recommendations(vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate actionable recommendations based on vulnerabilities.
    
    Args:
        vulnerabilities: List of vulnerability data.
        
    Returns:
        List of recommendation dictionaries.
    """
    try:
        recommendations = []
        
        # Count patchable and upgradeable vulnerabilities
        patchable_count = sum(1 for v in vulnerabilities if v.get("is_patchable"))
        upgradeable_count = sum(1 for v in vulnerabilities if v.get("is_upgradeable"))
        
        # High-priority recommendations
        if any(v.get("severity") == "critical" for v in vulnerabilities):
            recommendations.append({
                "priority": "critical",
                "action": "immediate_action",
                "title": "Address Critical Vulnerabilities Immediately",
                "description": "Critical severity vulnerabilities pose immediate security risks and should be addressed as a top priority.",
                "affected_count": sum(1 for v in vulnerabilities if v.get("severity") == "critical")
            })
        
        if patchable_count > 0:
            recommendations.append({
                "priority": "high",
                "action": "apply_patches",
                "title": f"Apply Available Patches ({patchable_count} vulnerabilities)",
                "description": "Some vulnerabilities have patches available. Apply these patches to resolve security issues.",
                "affected_count": patchable_count
            })
        
        if upgradeable_count > 0:
            recommendations.append({
                "priority": "high",
                "action": "upgrade_packages",
                "title": f"Upgrade Vulnerable Packages ({upgradeable_count} vulnerabilities)",
                "description": "Upgrade affected packages to versions that resolve known vulnerabilities.",
                "affected_count": upgradeable_count
            })
        
        # Package-specific recommendations
        package_vulns = {}
        for vuln in vulnerabilities:
            pkg = vuln.get("package", "unknown")
            if pkg not in package_vulns:
                package_vulns[pkg] = []
            package_vulns[pkg].append(vuln)
        
        # Find packages with multiple vulnerabilities
        problematic_packages = {pkg: vulns for pkg, vulns in package_vulns.items() if len(vulns) > 2}
        
        if problematic_packages:
            for pkg, vulns in list(problematic_packages.items())[:5]:  # Top 5 problematic packages
                recommendations.append({
                    "priority": "medium",
                    "action": "review_package",
                    "title": f"Review Package: {pkg}",
                    "description": f"Package '{pkg}' has {len(vulns)} vulnerabilities. Consider finding alternatives or upgrading.",
                    "affected_count": len(vulns)
                })
        
        # General recommendations
        if len(vulnerabilities) > 50:
            recommendations.append({
                "priority": "medium",
                "action": "security_audit",
                "title": "Conduct Security Audit",
                "description": "High number of vulnerabilities detected. Consider conducting a comprehensive security audit.",
                "affected_count": len(vulnerabilities)
            })
        
        # Monitoring recommendation
        recommendations.append({
            "priority": "low",
            "action": "continuous_monitoring",
            "title": "Enable Continuous Monitoring",
            "description": "Set up continuous vulnerability monitoring to catch new issues early.",
            "affected_count": 0
        })
        
        return recommendations[:10]  # Limit to top 10 recommendations
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return [{"error": str(e)}]


def format_vulnerability_details(vulnerability: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format detailed information for a single vulnerability.
    
    Args:
        vulnerability: Vulnerability data dictionary.
        
    Returns:
        Formatted vulnerability details.
    """
    try:
        return {
            "vulnerability_info": {
                "id": vulnerability.get("id", "N/A"),
                "title": vulnerability.get("title", "Unknown"),
                "severity": vulnerability.get("severity", "unknown"),
                "cvss_score": vulnerability.get("cvss_score", 0),
                "type": vulnerability.get("type", "unknown")
            },
            "affected_package": {
                "name": vulnerability.get("package", "unknown"),
                "version": vulnerability.get("version", "unknown"),
                "language": vulnerability.get("language", "unknown"),
                "package_manager": vulnerability.get("package_manager", "unknown")
            },
            "security_details": {
                "cve_ids": vulnerability.get("cve", []),
                "cwe_ids": vulnerability.get("cwe", []),
                "exploit_maturity": vulnerability.get("exploit_maturity", "unknown"),
                "description": vulnerability.get("description", "")
            },
            "remediation": {
                "is_patchable": vulnerability.get("is_patchable", False),
                "is_upgradeable": vulnerability.get("is_upgradeable", False),
                "upgrade_path": vulnerability.get("upgrade_path", []),
                "introduced_through": vulnerability.get("introduced_through", [])
            },
            "references": vulnerability.get("references", [])
        }
        
    except Exception as e:
        logger.error(f"Error formatting vulnerability details: {e}")
        return {"error": str(e)}


def create_executive_summary(scan_results: List["SnykScanResult"]) -> Dict[str, Any]:
    """
    Create an executive summary from multiple scan results.
    
    Args:
        scan_results: List of SnykScanResult objects.
        
    Returns:
        Executive summary dictionary.
    """
    try:
        total_projects = len(scan_results)
        successful_scans = sum(1 for result in scan_results if result.success)
        total_vulnerabilities = sum(len(result.vulnerabilities) for result in scan_results)
        
        # Aggregate severity counts
        severity_totals = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        for result in scan_results:
            for severity in severity_totals:
                if severity in result.summary:
                    severity_totals[severity] += result.summary[severity]
        
        # Calculate overall risk level
        if severity_totals["critical"] > 0:
            overall_risk = "critical"
        elif severity_totals["high"] > 5:
            overall_risk = "high"
        elif severity_totals["medium"] > 10:
            overall_risk = "medium"
        else:
            overall_risk = "low"
        
        return {
            "executive_summary": {
                "total_projects_scanned": total_projects,
                "successful_scans": successful_scans,
                "failed_scans": total_projects - successful_scans,
                "total_vulnerabilities": total_vulnerabilities,
                "overall_risk_level": overall_risk,
                "severity_distribution": severity_totals
            },
            "key_findings": {
                "highest_risk_projects": [
                    {
                        "project": result.project_path,
                        "vulnerabilities": len(result.vulnerabilities),
                        "critical_count": result.summary.get("critical", 0)
                    }
                    for result in sorted(scan_results, key=lambda x: len(x.vulnerabilities), reverse=True)[:5]
                    if result.success
                ],
                "remediation_opportunities": {
                    "total_patchable": sum(
                        sum(1 for v in result.vulnerabilities if v.get("is_patchable"))
                        for result in scan_results
                    ),
                    "total_upgradeable": sum(
                        sum(1 for v in result.vulnerabilities if v.get("is_upgradeable"))
                        for result in scan_results
                    )
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating executive summary: {e}")
        return {"error": str(e)}
