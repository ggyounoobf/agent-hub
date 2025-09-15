"""
Security report generator for creating comprehensive security assessment reports.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from shared.utils.logging import logger

# logger = setup_tool_logger('security.reports')


class SecurityReportGenerator:
    """Generate comprehensive security assessment reports."""

    def __init__(self):
        self.report_templates = {
            "executive": "Executive Summary Report",
            "technical": "Technical Security Report",
            "compliance": "Compliance Assessment Report",
            "quick": "Quick Security Scan Report",
        }

        # Risk severity mapping
        self.severity_levels = {
            "critical": {"score_range": (0, 40), "color": "#dc3545", "priority": 1},
            "high": {"score_range": (41, 60), "color": "#fd7e14", "priority": 2},
            "medium": {"score_range": (61, 80), "color": "#ffc107", "priority": 3},
            "low": {"score_range": (81, 90), "color": "#28a745", "priority": 4},
            "minimal": {"score_range": (91, 100), "color": "#17a2b8", "priority": 5},
        }

        # Compliance frameworks
        self.compliance_frameworks = {
            "owasp_top10": "OWASP Top 10 2021",
            "nist_cybersecurity": "NIST Cybersecurity Framework",
            "iso27001": "ISO 27001",
            "pci_dss": "PCI DSS",
            "gdpr": "GDPR Security Requirements",
        }

    def generate_comprehensive_report(
        self,
        security_data: Dict[str, Any],
        report_type: str = "technical",
        include_recommendations: bool = True,
        include_compliance: bool = False,
        compliance_framework: str = "owasp_top10",
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive security assessment report.

        Args:
            security_data: Security analysis results from various tools
            report_type: Type of report ('executive', 'technical', 'compliance', 'quick')
            include_recommendations: Whether to include remediation recommendations
            include_compliance: Whether to include compliance mapping
            compliance_framework: Framework to map against

        Returns:
            Dictionary containing the formatted security report
        """
        try:
            logger.info(f"Generating {report_type} security report")

            # Extract and normalize data
            normalized_data = self._normalize_security_data(security_data)

            # Calculate overall security posture
            security_posture = self._calculate_security_posture(normalized_data)

            # Generate report based on type
            if report_type == "executive":
                report = self._generate_executive_report(normalized_data, security_posture)
            elif report_type == "technical":
                report = self._generate_technical_report(normalized_data, security_posture)
            elif report_type == "compliance":
                report = self._generate_compliance_report(
                    normalized_data, security_posture, compliance_framework
                )
            else:  # quick
                report = self._generate_quick_report(normalized_data, security_posture)

            # Add recommendations if requested
            if include_recommendations:
                report["recommendations"] = self._generate_prioritized_recommendations(
                    normalized_data
                )

            # Add compliance mapping if requested
            if include_compliance:
                report["compliance_mapping"] = self._map_to_compliance_framework(
                    normalized_data, compliance_framework
                )

            # Add metadata
            report["metadata"] = {
                "report_type": report_type,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "report_version": "1.0",
                "assessment_scope": self._determine_assessment_scope(normalized_data),
                "data_sources": list(normalized_data.keys()),
            }

            logger.info("Security report generated successfully")
            return {"success": True, "report": report}

        except Exception as e:
            logger.error(f"Error generating security report: {e}")
            return {"success": False, "error": str(e)}

    def _normalize_security_data(self, security_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize security data from different analysis tools."""
        normalized = {"headers": {}, "ssl_tls": {}, "dns": {}, "general": {}}

        # Normalize header analysis data
        if "header_analysis" in security_data:
            header_data = security_data["header_analysis"]
            normalized["headers"] = {
                "score": header_data.get("security_score", 0),
                "grade": header_data.get("grade", "F"),
                "headers_present": header_data.get("headers_present", 0),
                "missing_headers": header_data.get("missing_headers", []),
                "analysis": header_data.get("headers_analysis", {}),
                "recommendations": header_data.get("recommendations", []),
            }

        # Normalize SSL/TLS analysis data
        if "ssl_analysis" in security_data:
            ssl_data = security_data["ssl_analysis"]
            normalized["ssl_tls"] = {
                "score": ssl_data.get("ssl_score", 0),
                "grade": ssl_data.get("grade", "F"),
                "certificate_analysis": ssl_data.get("certificate_analysis", {}),
                "protocol_analysis": ssl_data.get("protocol_analysis", {}),
                "recommendations": ssl_data.get("recommendations", []),
            }

        # Normalize DNS analysis data
        if "dns_analysis" in security_data:
            dns_data = security_data["dns_analysis"]
            normalized["dns"] = {
                "score": dns_data.get("dns_security_score", 0),
                "grade": dns_data.get("grade", "F"),
                "dnssec_status": dns_data.get("dnssec_status", {}),
                "email_security": dns_data.get("email_security", {}),
                "caa_analysis": dns_data.get("caa_analysis", {}),
                "recommendations": dns_data.get("recommendations", []),
            }

        # Extract general information
        normalized["general"] = {
            "url": security_data.get("url", "Unknown"),
            "domain": security_data.get("domain", "Unknown"),
            "overall_score": security_data.get("overall_security_score", 0),
            "overall_grade": security_data.get("overall_grade", "F"),
            "scan_timestamp": security_data.get("scan_timestamp", datetime.now().timestamp()),
        }

        return normalized

    def _calculate_security_posture(self, normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall security posture metrics."""
        scores = []
        categories = ["headers", "ssl_tls", "dns"]

        category_scores = {}
        for category in categories:
            if category in normalized_data and "score" in normalized_data[category]:
                score = normalized_data[category]["score"]
                scores.append(score)
                category_scores[category] = score

        overall_score = sum(scores) / len(scores) if scores else 0
        overall_grade = self._score_to_grade(overall_score)
        risk_level = self._score_to_risk_level(overall_score)

        return {
            "overall_score": round(overall_score, 1),
            "overall_grade": overall_grade,
            "risk_level": risk_level,
            "category_scores": category_scores,
            "total_categories_assessed": len(scores),
            "score_distribution": self._calculate_score_distribution(scores),
        }

    def _generate_executive_report(
        self, normalized_data: Dict[str, Any], security_posture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate executive summary report."""
        return {
            "report_title": "Executive Security Assessment Summary",
            "executive_summary": {
                "overall_security_score": security_posture["overall_score"],
                "overall_grade": security_posture["overall_grade"],
                "risk_level": security_posture["risk_level"],
                "key_findings": self._extract_key_findings(normalized_data),
                "critical_issues": self._extract_critical_issues(normalized_data),
                "immediate_actions": self._extract_immediate_actions(normalized_data),
            },
            "security_overview": {
                "categories_assessed": security_posture["total_categories_assessed"],
                "score_breakdown": security_posture["category_scores"],
                "compliance_status": self._assess_basic_compliance(normalized_data),
            },
            "risk_assessment": {
                "overall_risk": security_posture["risk_level"],
                "risk_factors": self._identify_risk_factors(normalized_data),
                "business_impact": self._assess_business_impact(security_posture["risk_level"]),
            },
            "next_steps": self._generate_executive_next_steps(normalized_data, security_posture),
        }

    def _generate_technical_report(
        self, normalized_data: Dict[str, Any], security_posture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate detailed technical security report."""
        return {
            "report_title": "Technical Security Assessment Report",
            "assessment_summary": {
                "overall_score": security_posture["overall_score"],
                "overall_grade": security_posture["overall_grade"],
                "risk_level": security_posture["risk_level"],
                "assessment_scope": self._determine_assessment_scope(normalized_data),
            },
            "detailed_findings": {
                "http_security_headers": self._format_headers_findings(
                    normalized_data.get("headers", {})
                ),
                "ssl_tls_configuration": self._format_ssl_findings(
                    normalized_data.get("ssl_tls", {})
                ),
                "dns_security": self._format_dns_findings(normalized_data.get("dns", {})),
            },
            "vulnerability_analysis": {
                "critical_vulnerabilities": self._extract_critical_vulnerabilities(normalized_data),
                "medium_risk_issues": self._extract_medium_risk_issues(normalized_data),
                "low_risk_observations": self._extract_low_risk_observations(normalized_data),
            },
            "technical_recommendations": {
                "immediate_fixes": self._categorize_recommendations(normalized_data, "immediate"),
                "short_term_improvements": self._categorize_recommendations(
                    normalized_data, "short_term"
                ),
                "long_term_enhancements": self._categorize_recommendations(
                    normalized_data, "long_term"
                ),
            },
            "implementation_guidance": self._generate_implementation_guidance(normalized_data),
        }

    def _generate_compliance_report(
        self, normalized_data: Dict[str, Any], security_posture: Dict[str, Any], framework: str
    ) -> Dict[str, Any]:
        """Generate compliance-focused security report."""
        compliance_mapping = self._map_to_compliance_framework(normalized_data, framework)

        return {
            "report_title": f"Security Compliance Assessment - {self.compliance_frameworks.get(framework, framework)}",
            "compliance_summary": {
                "framework": self.compliance_frameworks.get(framework, framework),
                "overall_compliance_score": compliance_mapping["overall_compliance_score"],
                "compliant_controls": compliance_mapping["compliant_controls"],
                "non_compliant_controls": compliance_mapping["non_compliant_controls"],
                "partial_compliance": compliance_mapping["partial_compliance"],
            },
            "control_assessment": compliance_mapping["control_details"],
            "gap_analysis": {
                "critical_gaps": compliance_mapping["critical_gaps"],
                "remediation_priority": compliance_mapping["remediation_priority"],
            },
            "compliance_roadmap": self._generate_compliance_roadmap(compliance_mapping),
        }

    def _generate_quick_report(
        self, normalized_data: Dict[str, Any], security_posture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate quick security scan report."""
        return {
            "report_title": "Quick Security Scan Report",
            "scan_summary": {
                "overall_score": security_posture["overall_score"],
                "overall_grade": security_posture["overall_grade"],
                "risk_level": security_posture["risk_level"],
                "scan_coverage": security_posture["total_categories_assessed"],
            },
            "key_findings": {
                "critical_issues": len(self._extract_critical_issues(normalized_data)),
                "security_headers_status": normalized_data.get("headers", {}).get(
                    "grade", "Not Assessed"
                ),
                "ssl_tls_status": normalized_data.get("ssl_tls", {}).get("grade", "Not Assessed"),
                "dns_security_status": normalized_data.get("dns", {}).get("grade", "Not Assessed"),
            },
            "top_recommendations": self._get_top_recommendations(normalized_data, limit=5),
            "score_breakdown": security_posture["category_scores"],
        }

    def _extract_key_findings(self, normalized_data: Dict[str, Any]) -> List[str]:
        """Extract key security findings."""
        findings = []

        # Headers findings
        headers_data = normalized_data.get("headers", {})
        if headers_data.get("score", 0) < 70:
            findings.append(
                f"HTTP security headers need improvement (Score: {headers_data.get('score', 0)}/100)"
            )

        # SSL/TLS findings
        ssl_data = normalized_data.get("ssl_tls", {})
        if ssl_data.get("score", 0) < 70:
            findings.append(
                f"SSL/TLS configuration requires attention (Score: {ssl_data.get('score', 0)}/100)"
            )

        # DNS findings
        dns_data = normalized_data.get("dns", {})
        if dns_data.get("score", 0) < 70:
            findings.append(
                f"DNS security configuration needs enhancement (Score: {dns_data.get('score', 0)}/100)"
            )

        # DNSSEC
        if not dns_data.get("dnssec_status", {}).get("enabled"):
            findings.append("DNSSEC is not enabled - domain vulnerable to DNS attacks")

        # Email security
        email_security = dns_data.get("email_security", {})
        if not email_security.get("dmarc", {}).get("present"):
            findings.append("DMARC policy not implemented - email domain vulnerable to spoofing")

        return findings[:8]  # Limit to top 8 findings

    def _extract_critical_issues(self, normalized_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract critical security issues."""
        critical_issues = []

        # Check for critical security header issues
        headers_data = normalized_data.get("headers", {})
        missing_headers = headers_data.get("missing_headers", [])
        for header in missing_headers:
            if header.get("severity") == "high":
                critical_issues.append(
                    {
                        "category": "HTTP Security Headers",
                        "issue": f"Missing {header.get('name', 'Unknown Header')}",
                        "severity": "Critical",
                        "description": header.get("purpose", "Security header not implemented"),
                        "recommendation": header.get("recommendation", "Implement security header"),
                    }
                )

        # Check for SSL/TLS critical issues
        ssl_data = normalized_data.get("ssl_tls", {})
        cert_analysis = ssl_data.get("certificate_analysis", {})
        for issue in cert_analysis.get("issues", []):
            if "expired" in issue.lower() or "sha-1" in issue.lower():
                critical_issues.append(
                    {
                        "category": "SSL/TLS Configuration",
                        "issue": issue,
                        "severity": "Critical",
                        "description": "SSL certificate or configuration issue",
                        "recommendation": "Update SSL certificate or configuration",
                    }
                )

        return critical_issues[:10]  # Limit to top 10 critical issues

    def _extract_immediate_actions(self, normalized_data: Dict[str, Any]) -> List[str]:
        """Extract immediate action items."""
        actions = []

        # Critical SSL issues
        ssl_data = normalized_data.get("ssl_tls", {})
        cert_analysis = ssl_data.get("certificate_analysis", {})
        for issue in cert_analysis.get("issues", []):
            if "expired" in issue.lower():
                actions.append("Renew expired SSL certificate immediately")
            elif "expires soon" in issue.lower():
                actions.append("Schedule SSL certificate renewal")

        # Missing critical headers
        headers_data = normalized_data.get("headers", {})
        missing_critical = [
            h for h in headers_data.get("missing_headers", []) if h.get("severity") == "high"
        ]
        if missing_critical:
            actions.append("Implement critical HTTP security headers (HSTS, CSP)")

        # DNSSEC
        dns_data = normalized_data.get("dns", {})
        if not dns_data.get("dnssec_status", {}).get("enabled"):
            actions.append("Enable DNSSEC for DNS security")

        # DMARC
        email_security = dns_data.get("email_security", {})
        if not email_security.get("dmarc", {}).get("present"):
            actions.append("Implement DMARC policy for email security")

        return actions[:5]  # Limit to top 5 immediate actions

    def _generate_prioritized_recommendations(
        self, normalized_data: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Generate prioritized security recommendations."""
        recommendations = {"critical": [], "high": [], "medium": [], "low": []}

        # Collect all recommendations from different analyses
        all_recommendations = []

        for category in ["headers", "ssl_tls", "dns"]:
            category_data = normalized_data.get(category, {})
            category_recommendations = category_data.get("recommendations", [])
            for rec in category_recommendations:
                all_recommendations.append(
                    {
                        "category": category,
                        "recommendation": rec,
                        "priority": self._determine_recommendation_priority(rec),
                    }
                )

        # Sort by priority
        for rec in all_recommendations:
            priority = rec["priority"]
            if priority in recommendations:
                recommendations[priority].append(
                    {
                        "category": rec["category"].replace("_", " ").title(),
                        "action": rec["recommendation"],
                    }
                )

        return recommendations

    def _map_to_compliance_framework(
        self, normalized_data: Dict[str, Any], framework: str
    ) -> Dict[str, Any]:
        """Map security findings to compliance framework."""
        if framework == "owasp_top10":
            return self._map_to_owasp_top10(normalized_data)
        elif framework == "nist_cybersecurity":
            return self._map_to_nist_framework(normalized_data)
        else:
            return {
                "overall_compliance_score": 0,
                "compliant_controls": 0,
                "non_compliant_controls": 0,
                "partial_compliance": 0,
                "control_details": {},
                "critical_gaps": [],
                "remediation_priority": [],
            }

    def _map_to_owasp_top10(self, normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map findings to OWASP Top 10 2021."""
        owasp_mapping = {
            "A01_Broken_Access_Control": {"compliant": False, "findings": []},
            "A02_Cryptographic_Failures": {"compliant": True, "findings": []},
            "A03_Injection": {"compliant": False, "findings": []},
            "A04_Insecure_Design": {"compliant": False, "findings": []},
            "A05_Security_Misconfiguration": {"compliant": False, "findings": []},
            "A06_Vulnerable_Components": {"compliant": False, "findings": []},
            "A07_Authentication_Failures": {"compliant": False, "findings": []},
            "A08_Software_Data_Integrity": {"compliant": False, "findings": []},
            "A09_Security_Logging_Monitoring": {"compliant": False, "findings": []},
            "A10_Server_Side_Request_Forgery": {"compliant": False, "findings": []},
        }

        # A02: Cryptographic Failures - SSL/TLS
        ssl_data = normalized_data.get("ssl_tls", {})
        if ssl_data.get("score", 0) >= 80:
            owasp_mapping["A02_Cryptographic_Failures"]["compliant"] = True
        else:
            owasp_mapping["A02_Cryptographic_Failures"]["findings"].append(
                "SSL/TLS configuration issues detected"
            )

        # A05: Security Misconfiguration - Headers
        headers_data = normalized_data.get("headers", {})
        if headers_data.get("score", 0) >= 80:
            owasp_mapping["A05_Security_Misconfiguration"]["compliant"] = True
        else:
            owasp_mapping["A05_Security_Misconfiguration"]["findings"].append(
                "HTTP security headers misconfigured"
            )

        # Calculate compliance metrics
        compliant_controls = sum(1 for control in owasp_mapping.values() if control["compliant"])
        non_compliant_controls = len(owasp_mapping) - compliant_controls
        overall_score = round((compliant_controls / len(owasp_mapping)) * 100, 1)

        return {
            "overall_compliance_score": overall_score,
            "compliant_controls": compliant_controls,
            "non_compliant_controls": non_compliant_controls,
            "partial_compliance": 0,
            "control_details": owasp_mapping,
            "critical_gaps": self._identify_critical_owasp_gaps(owasp_mapping),
            "remediation_priority": self._prioritize_owasp_remediation(owasp_mapping),
        }

    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade."""
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

    def _score_to_risk_level(self, score: float) -> str:
        """Convert score to risk level."""
        for level, config in self.severity_levels.items():
            score_range = config["score_range"]
            if score_range[0] <= score <= score_range[1]:
                return level.title()
        return "Unknown"

    def _determine_recommendation_priority(self, recommendation: str) -> str:
        """Determine priority level of a recommendation."""
        critical_keywords = ["expired", "critical", "immediately", "urgent"]
        high_keywords = ["missing", "implement", "enable", "vulnerable"]
        medium_keywords = ["improve", "upgrade", "consider", "enhance"]

        rec_lower = recommendation.lower()

        if any(keyword in rec_lower for keyword in critical_keywords):
            return "critical"
        elif any(keyword in rec_lower for keyword in high_keywords):
            return "high"
        elif any(keyword in rec_lower for keyword in medium_keywords):
            return "medium"
        else:
            return "low"

    def _calculate_score_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Calculate distribution of scores across risk levels."""
        distribution = {"critical": 0, "high": 0, "medium": 0, "low": 0, "minimal": 0}

        for score in scores:
            risk_level = self._score_to_risk_level(score).lower()
            if risk_level in distribution:
                distribution[risk_level] += 1

        return distribution

    def _format_headers_findings(self, headers_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format HTTP security headers findings."""
        if not headers_data:
            return {"status": "Not assessed"}

        return {
            "overall_score": headers_data.get("score", 0),
            "grade": headers_data.get("grade", "F"),
            "headers_present": headers_data.get("headers_present", 0),
            "missing_critical_headers": [
                h for h in headers_data.get("missing_headers", []) if h.get("severity") == "high"
            ],
            "improvement_areas": headers_data.get("recommendations", []),
        }

    def _format_ssl_findings(self, ssl_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format SSL/TLS findings."""
        if not ssl_data:
            return {"status": "Not assessed"}

        return {
            "overall_score": ssl_data.get("score", 0),
            "grade": ssl_data.get("grade", "F"),
            "certificate_status": ssl_data.get("certificate_analysis", {}),
            "protocol_support": ssl_data.get("protocol_analysis", {}),
            "improvement_areas": ssl_data.get("recommendations", []),
        }

    def _format_dns_findings(self, dns_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format DNS security findings."""
        if not dns_data:
            return {"status": "Not assessed"}

        return {
            "overall_score": dns_data.get("score", 0),
            "grade": dns_data.get("grade", "F"),
            "dnssec_enabled": dns_data.get("dnssec_status", {}).get("enabled", False),
            "email_security_status": dns_data.get("email_security", {}),
            "caa_records_present": dns_data.get("caa_analysis", {}).get("present", False),
            "improvement_areas": dns_data.get("recommendations", []),
        }

    def generate_report_summary(self, reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of multiple security reports."""
        try:
            if not reports:
                return {"success": False, "error": "No reports provided"}

            # Calculate summary statistics
            total_reports = len(reports)
            successful_reports = len([r for r in reports if r.get("success")])

            # Extract scores
            all_scores = []
            for report in reports:
                if report.get("success") and "report" in report:
                    report_data = report["report"]
                    if "assessment_summary" in report_data:
                        score = report_data["assessment_summary"].get("overall_score", 0)
                        all_scores.append(score)
                    elif "scan_summary" in report_data:
                        score = report_data["scan_summary"].get("overall_score", 0)
                        all_scores.append(score)

            # Calculate summary metrics
            avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
            min_score = min(all_scores) if all_scores else 0
            max_score = max(all_scores) if all_scores else 0

            return {
                "success": True,
                "summary": {
                    "total_reports": total_reports,
                    "successful_assessments": successful_reports,
                    "average_security_score": avg_score,
                    "minimum_score": min_score,
                    "maximum_score": max_score,
                    "overall_grade": self._score_to_grade(avg_score),
                    "risk_distribution": self._calculate_score_distribution(all_scores),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"Error generating report summary: {e}")
            return {"success": False, "error": str(e)}

    def export_report_formats(
        self, report: Dict[str, Any], formats: List[str] = ["json", "markdown"]
    ) -> Dict[str, Any]:
        """Export report in different formats."""
        exports = {}

        try:
            if "json" in formats:
                exports["json"] = json.dumps(report, indent=2, default=str)

            if "markdown" in formats:
                exports["markdown"] = self._convert_to_markdown(report)

            if "html" in formats:
                exports["html"] = self._convert_to_html(report)

            return {"success": True, "exports": exports}

        except Exception as e:
            logger.error(f"Error exporting report formats: {e}")
            return {"success": False, "error": str(e)}

    def _convert_to_markdown(self, report: Dict[str, Any]) -> str:
        """Convert report to Markdown format."""
        md_content = []

        # Title
        title = report.get("report_title", "Security Assessment Report")
        md_content.append(f"# {title}\n")

        # Executive Summary or Assessment Summary
        if "executive_summary" in report:
            summary = report["executive_summary"]
            md_content.append("## Executive Summary\n")
            md_content.append(
                f"**Overall Security Score:** {summary.get('overall_security_score', 'N/A')}/100 (Grade: {summary.get('overall_grade', 'N/A')})\n"
            )
            md_content.append(f"**Risk Level:** {summary.get('risk_level', 'Unknown')}\n\n")

            if "key_findings" in summary:
                md_content.append("### Key Findings\n")
                for finding in summary["key_findings"]:
                    md_content.append(f"- {finding}\n")
                md_content.append("\n")

        elif "assessment_summary" in report:
            summary = report["assessment_summary"]
            md_content.append("## Assessment Summary\n")
            md_content.append(
                f"**Overall Score:** {summary.get('overall_score', 'N/A')}/100 (Grade: {summary.get('overall_grade', 'N/A')})\n"
            )
            md_content.append(f"**Risk Level:** {summary.get('risk_level', 'Unknown')}\n\n")

        # Recommendations
        if "recommendations" in report:
            md_content.append("## Recommendations\n")
            recommendations = report["recommendations"]

            for priority in ["critical", "high", "medium", "low"]:
                if priority in recommendations and recommendations[priority]:
                    md_content.append(f"### {priority.title()} Priority\n")
                    for rec in recommendations[priority]:
                        if isinstance(rec, dict):
                            md_content.append(
                                f"- **{rec.get('category', 'General')}:** {rec.get('action', 'No action specified')}\n"
                            )
                        else:
                            md_content.append(f"- {rec}\n")
                    md_content.append("\n")

        # Metadata
        if "metadata" in report:
            metadata = report["metadata"]
            md_content.append("## Report Information\n")
            md_content.append(f"**Generated:** {metadata.get('generated_at', 'Unknown')}\n")
            md_content.append(f"**Report Type:** {metadata.get('report_type', 'Unknown')}\n")
            md_content.append(
                f"**Assessment Scope:** {metadata.get('assessment_scope', 'Unknown')}\n"
            )

        return "".join(md_content)

    def _convert_to_html(self, report: Dict[str, Any]) -> str:
        """Convert report to HTML format."""
        # Simple HTML conversion - could be enhanced with templates
        markdown_content = self._convert_to_markdown(report)

        # Basic Markdown to HTML conversion
        html_content = (
            markdown_content.replace("\n# ", "\n<h1>")
            .replace("\n## ", "\n<h2>")
            .replace("\n### ", "\n<h3>")
        )
        html_content = html_content.replace("**", "<strong>").replace("**", "</strong>")
        html_content = html_content.replace("\n- ", "\n<li>").replace("\n\n", "</li>\n\n")
        html_content = html_content.replace("\n", "<br>\n")

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Security Assessment Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1, h2, h3 {{ color: #333; }}
                .critical {{ color: #dc3545; }}
                .high {{ color: #fd7e14; }}
                .medium {{ color: #ffc107; }}
                .low {{ color: #28a745; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

    # Helper methods for detailed analysis
    def _determine_assessment_scope(self, normalized_data: Dict[str, Any]) -> str:
        """Determine the scope of the security assessment."""
        scopes = []
        if "headers" in normalized_data:
            scopes.append("HTTP Security Headers")
        if "ssl_tls" in normalized_data:
            scopes.append("SSL/TLS Configuration")
        if "dns" in normalized_data:
            scopes.append("DNS Security")

        return ", ".join(scopes) if scopes else "Limited Assessment"

    def _assess_basic_compliance(self, normalized_data: Dict[str, Any]) -> str:
        """Assess basic compliance status."""
        total_score = 0
        count = 0

        for category in ["headers", "ssl_tls", "dns"]:
            if category in normalized_data and "score" in normalized_data[category]:
                total_score += normalized_data[category]["score"]
                count += 1

        avg_score = total_score / count if count > 0 else 0

        if avg_score >= 80:
            return "Good compliance posture"
        elif avg_score >= 60:
            return "Moderate compliance gaps"
        else:
            return "Significant compliance issues"

    def _identify_risk_factors(self, normalized_data: Dict[str, Any]) -> List[str]:
        """Identify key risk factors."""
        risk_factors = []

        # DNS risks
        dns_data = normalized_data.get("dns", {})
        if not dns_data.get("dnssec_status", {}).get("enabled"):
            risk_factors.append("DNSSEC not enabled - DNS spoofing risk")

        # SSL risks
        ssl_data = normalized_data.get("ssl_tls", {})
        if ssl_data.get("score", 0) < 70:
            risk_factors.append("SSL/TLS configuration weaknesses")

        # Header risks
        headers_data = normalized_data.get("headers", {})
        if headers_data.get("score", 0) < 70:
            risk_factors.append("Missing security headers - XSS/clickjacking risk")

        return risk_factors

    def _assess_business_impact(self, risk_level: str) -> str:
        """Assess business impact based on risk level."""
        impact_mapping = {
            "critical": "High business risk - immediate action required",
            "high": "Moderate business risk - prompt attention needed",
            "medium": "Low to moderate business risk - schedule improvements",
            "low": "Minimal business risk - maintain current security posture",
            "minimal": "Very low business risk - excellent security posture",
        }

        return impact_mapping.get(risk_level.lower(), "Unknown business impact")

    def _generate_executive_next_steps(
        self, normalized_data: Dict[str, Any], security_posture: Dict[str, Any]
    ) -> List[str]:
        """Generate executive-level next steps."""
        next_steps = []

        risk_level = security_posture["risk_level"].lower()

        if risk_level in ["critical", "high"]:
            next_steps.append("Assign dedicated security team to address critical issues")
            next_steps.append("Implement emergency security patches within 48 hours")
            next_steps.append("Schedule comprehensive security audit")
        elif risk_level == "medium":
            next_steps.append("Develop 30-day security improvement plan")
            next_steps.append("Allocate budget for security enhancements")
            next_steps.append("Train development team on secure coding practices")
        else:
            next_steps.append("Maintain current security monitoring")
            next_steps.append("Schedule quarterly security reviews")
            next_steps.append("Consider advanced security features")

        return next_steps

    def _categorize_recommendations(
        self, normalized_data: Dict[str, Any], timeframe: str
    ) -> List[str]:
        """Categorize recommendations by implementation timeframe."""
        all_recommendations = []

        # Collect all recommendations
        for category in ["headers", "ssl_tls", "dns"]:
            category_data = normalized_data.get(category, {})
            recommendations = category_data.get("recommendations", [])
            all_recommendations.extend(recommendations)

        # Categorize by timeframe
        timeframe_mapping = {
            "immediate": ["expired", "critical", "urgent", "immediately"],
            "short_term": ["implement", "enable", "add", "configure"],
            "long_term": ["upgrade", "enhance", "consider", "improve"],
        }

        keywords = timeframe_mapping.get(timeframe, [])
        categorized = []

        for rec in all_recommendations:
            rec_lower = rec.lower()
            if any(keyword in rec_lower for keyword in keywords):
                categorized.append(rec)

        return categorized[:5]  # Limit to 5 per category

    def _generate_implementation_guidance(
        self, normalized_data: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Generate technical implementation guidance."""
        guidance = {"security_headers": [], "ssl_tls": [], "dns_security": []}

        # Headers guidance
        headers_data = normalized_data.get("headers", {})
        missing_headers = headers_data.get("missing_headers", [])
        for header in missing_headers:
            if header.get("header") == "strict-transport-security":
                guidance["security_headers"].append(
                    "Add HSTS header: Strict-Transport-Security: max-age=31536000; includeSubDomains"
                )
            elif header.get("header") == "content-security-policy":
                guidance["security_headers"].append(
                    "Implement CSP: Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'"
                )

        # SSL guidance
        ssl_data = normalized_data.get("ssl_tls", {})
        ssl_recommendations = ssl_data.get("recommendations", [])
        guidance["ssl_tls"] = ssl_recommendations[:3]  # Top 3

        # DNS guidance
        dns_data = normalized_data.get("dns", {})
        dns_recommendations = dns_data.get("recommendations", [])
        guidance["dns_security"] = dns_recommendations[:3]  # Top 3

        return guidance

    def _extract_critical_vulnerabilities(
        self, normalized_data: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Extract critical vulnerabilities from analysis."""
        vulnerabilities = []

        # SSL vulnerabilities
        ssl_data = normalized_data.get("ssl_tls", {})
        cert_analysis = ssl_data.get("certificate_analysis", {})
        for issue in cert_analysis.get("issues", []):
            if "expired" in issue.lower() or "weak" in issue.lower():
                vulnerabilities.append(
                    {"category": "SSL/TLS", "vulnerability": issue, "severity": "Critical"}
                )

        # Header vulnerabilities
        headers_data = normalized_data.get("headers", {})
        missing_critical = [
            h for h in headers_data.get("missing_headers", []) if h.get("severity") == "high"
        ]
        for header in missing_critical:
            vulnerabilities.append(
                {
                    "category": "HTTP Headers",
                    "vulnerability": f"Missing {header.get('name')}",
                    "severity": "High",
                }
            )

        return vulnerabilities

    def _extract_medium_risk_issues(self, normalized_data: Dict[str, Any]) -> List[str]:
        """Extract medium risk security issues."""
        issues = []

        # Medium severity headers
        headers_data = normalized_data.get("headers", {})
        missing_medium = [
            h for h in headers_data.get("missing_headers", []) if h.get("severity") == "medium"
        ]
        for header in missing_medium:
            issues.append(f"Missing {header.get('name')} header")

        # DNS issues
        dns_data = normalized_data.get("dns", {})
        if not dns_data.get("caa_analysis", {}).get("present"):
            issues.append("No CAA records configured")

        return issues

    def _extract_low_risk_observations(self, normalized_data: Dict[str, Any]) -> List[str]:
        """Extract low risk observations."""
        observations = []

        # Low severity headers
        headers_data = normalized_data.get("headers", {})
        missing_low = [
            h for h in headers_data.get("missing_headers", []) if h.get("severity") == "low"
        ]
        for header in missing_low:
            observations.append(f"Consider implementing {header.get('name')} header")

        return observations

    def _get_top_recommendations(
        self, normalized_data: Dict[str, Any], limit: int = 5
    ) -> List[str]:
        """Get top recommendations across all categories."""
        all_recommendations = []

        for category in ["headers", "ssl_tls", "dns"]:
            category_data = normalized_data.get(category, {})
            recommendations = category_data.get("recommendations", [])
            all_recommendations.extend(recommendations)

        # Prioritize recommendations
        prioritized = []
        for rec in all_recommendations:
            priority = self._determine_recommendation_priority(rec)
            prioritized.append((rec, priority))

        # Sort by priority (critical first)
        priority_order = {"critical": 1, "high": 2, "medium": 3, "low": 4}
        prioritized.sort(key=lambda x: priority_order.get(x[1], 5))

        return [rec[0] for rec in prioritized[:limit]]

    def _identify_critical_owasp_gaps(self, owasp_mapping: Dict[str, Any]) -> List[str]:
        """Identify critical OWASP compliance gaps."""
        critical_gaps = []

        critical_controls = ["A02_Cryptographic_Failures", "A05_Security_Misconfiguration"]

        for control in critical_controls:
            if control in owasp_mapping and not owasp_mapping[control]["compliant"]:
                control_name = (
                    control.replace("_", " ").replace("A02", "A02:").replace("A05", "A05:")
                )
                critical_gaps.append(control_name)

        return critical_gaps

    def _prioritize_owasp_remediation(self, owasp_mapping: Dict[str, Any]) -> List[str]:
        """Prioritize OWASP remediation efforts."""
        remediation = []

        # Priority order for OWASP controls
        priority_controls = [
            ("A02_Cryptographic_Failures", "Fix SSL/TLS and cryptographic implementations"),
            (
                "A05_Security_Misconfiguration",
                "Implement proper security headers and configurations",
            ),
            ("A03_Injection", "Implement input validation and parameterized queries"),
        ]

        for control, action in priority_controls:
            if control in owasp_mapping and not owasp_mapping[control]["compliant"]:
                remediation.append(action)

        return remediation

    def _generate_compliance_roadmap(
        self, compliance_mapping: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate compliance roadmap."""
        roadmap = []

        # Phase 1: Critical gaps
        if compliance_mapping["critical_gaps"]:
            roadmap.append(
                {
                    "phase": "Phase 1 (0-30 days)",
                    "focus": "Critical Security Gaps",
                    "actions": ", ".join(compliance_mapping["critical_gaps"]),
                }
            )

        # Phase 2: High priority remediation
        if compliance_mapping["remediation_priority"]:
            roadmap.append(
                {
                    "phase": "Phase 2 (30-90 days)",
                    "focus": "Security Improvements",
                    "actions": ", ".join(compliance_mapping["remediation_priority"][:3]),
                }
            )

        # Phase 3: Ongoing monitoring
        roadmap.append(
            {
                "phase": "Phase 3 (Ongoing)",
                "focus": "Continuous Monitoring",
                "actions": "Regular security assessments, vulnerability scanning, compliance monitoring",
            }
        )

        return roadmap

    def _map_to_nist_framework(self, normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map findings to NIST Cybersecurity Framework."""
        # Simplified NIST mapping - would be expanded in full implementation
        return {
            "overall_compliance_score": 75,
            "compliant_controls": 3,
            "non_compliant_controls": 2,
            "partial_compliance": 0,
            "control_details": {
                "PR.DS-2": {"compliant": True, "description": "Data-in-transit protection via TLS"},
                "PR.AC-3": {"compliant": False, "description": "Remote access management"},
            },
            "critical_gaps": ["Access Control", "Asset Management"],
            "remediation_priority": ["Implement access controls", "Asset inventory management"],
        }
