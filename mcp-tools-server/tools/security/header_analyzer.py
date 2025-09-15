"""
Security headers analysis for web applications.
"""

import asyncio
from typing import Any, Dict
from urllib.parse import urlparse

import aiohttp

from shared.utils.logging import logger

# logger = setup_tool_logger('security.headers')


class SecurityHeaderAnalyzer:
    """Analyze HTTP security headers for common vulnerabilities."""

    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=30)

        # Security headers to check
        self.security_headers = {
            "strict-transport-security": {
                "name": "HTTP Strict Transport Security (HSTS)",
                "purpose": "Enforces HTTPS connections",
                "severity": "high",
                "recommendation": "Add HSTS header with max-age directive",
            },
            "content-security-policy": {
                "name": "Content Security Policy (CSP)",
                "purpose": "Prevents XSS and data injection attacks",
                "severity": "high",
                "recommendation": "Implement comprehensive CSP policy",
            },
            "x-frame-options": {
                "name": "X-Frame-Options",
                "purpose": "Prevents clickjacking attacks",
                "severity": "medium",
                "recommendation": "Set to DENY or SAMEORIGIN",
            },
            "x-content-type-options": {
                "name": "X-Content-Type-Options",
                "purpose": "Prevents MIME type sniffing",
                "severity": "medium",
                "recommendation": "Set to nosniff",
            },
            "referrer-policy": {
                "name": "Referrer Policy",
                "purpose": "Controls referrer information",
                "severity": "low",
                "recommendation": "Set appropriate referrer policy",
            },
            "permissions-policy": {
                "name": "Permissions Policy",
                "purpose": "Controls browser features",
                "severity": "low",
                "recommendation": "Configure feature permissions",
            },
            "x-xss-protection": {
                "name": "X-XSS-Protection",
                "purpose": "Enables XSS filtering (legacy)",
                "severity": "low",
                "recommendation": "Set to 1; mode=block (CSP preferred)",
            },
        }

    async def analyze_headers(self, url: str) -> Dict[str, Any]:
        """
        Analyze security headers for a given URL.

        Args:
            url: Target URL to analyze

        Returns:
            Dictionary with header analysis results
        """
        try:
            logger.info(f"Starting security header analysis for: {url}")

            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return {"success": False, "error": "Invalid URL format"}

            # Ensure HTTPS for security headers analysis
            if parsed_url.scheme == "http":
                logger.warning(f"HTTP URL detected, security headers may be limited: {url}")

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, allow_redirects=True) as response:
                    headers = dict(response.headers)
                    status_code = response.status
                    final_url = str(response.url)

                    # Analyze headers
                    analysis = self._analyze_security_headers(headers)

                    # Calculate security score
                    security_score = self._calculate_security_score(analysis["headers_analysis"])

                    return {
                        "success": True,
                        "url": url,
                        "final_url": final_url,
                        "status_code": status_code,
                        "is_https": final_url.startswith("https://"),
                        "security_score": security_score,
                        "grade": self._get_security_grade(security_score),
                        "headers_analysis": analysis["headers_analysis"],
                        "missing_headers": analysis["missing_headers"],
                        "recommendations": analysis["recommendations"],
                        "total_headers_checked": len(self.security_headers),
                        "headers_present": analysis["headers_present"],
                        "analysis_timestamp": asyncio.get_event_loop().time(),
                    }

        except asyncio.TimeoutError:
            logger.error(f"Timeout analyzing headers for: {url}")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error analyzing headers for {url}: {e}")
            return {"success": False, "error": str(e)}

    def _analyze_security_headers(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Analyze individual security headers."""
        headers_lower = {k.lower(): v for k, v in headers.items()}

        headers_analysis = {}
        missing_headers = []
        recommendations = []
        headers_present = 0

        for header_key, header_info in self.security_headers.items():
            if header_key in headers_lower:
                headers_present += 1
                value = headers_lower[header_key]

                # Analyze specific header
                analysis = self._analyze_specific_header(header_key, value)
                headers_analysis[header_key] = {
                    "present": True,
                    "value": value,
                    "analysis": analysis,
                    "severity": header_info["severity"],
                    "name": header_info["name"],
                }

                # Add recommendations if needed
                if analysis.get("issues"):
                    recommendations.extend(analysis["issues"])

            else:
                missing_headers.append(
                    {
                        "header": header_key,
                        "name": header_info["name"],
                        "purpose": header_info["purpose"],
                        "severity": header_info["severity"],
                        "recommendation": header_info["recommendation"],
                    }
                )

                headers_analysis[header_key] = {
                    "present": False,
                    "severity": header_info["severity"],
                    "name": header_info["name"],
                    "recommendation": header_info["recommendation"],
                }

        return {
            "headers_analysis": headers_analysis,
            "missing_headers": missing_headers,
            "recommendations": recommendations,
            "headers_present": headers_present,
        }

    def _analyze_specific_header(self, header: str, value: str) -> Dict[str, Any]:
        """Analyze specific security header values."""
        analysis = {"issues": [], "strengths": []}

        if header == "strict-transport-security":
            return self._analyze_hsts(value)
        elif header == "content-security-policy":
            return self._analyze_csp(value)
        elif header == "x-frame-options":
            return self._analyze_frame_options(value)
        elif header == "x-content-type-options":
            return self._analyze_content_type_options(value)
        elif header == "referrer-policy":
            return self._analyze_referrer_policy(value)
        elif header == "x-xss-protection":
            return self._analyze_xss_protection(value)

        return analysis

    def _analyze_hsts(self, value: str) -> Dict[str, Any]:
        """Analyze HSTS header."""
        analysis = {"issues": [], "strengths": []}

        if "max-age=" in value:
            # Extract max-age value
            try:
                max_age_part = [part for part in value.split(";") if "max-age=" in part][0]
                max_age = int(max_age_part.split("=")[1].strip())

                if max_age < 31536000:  # Less than 1 year
                    analysis["issues"].append(
                        "HSTS max-age should be at least 1 year (31536000 seconds)"
                    )
                else:
                    analysis["strengths"].append(f"Good HSTS max-age: {max_age} seconds")

                if "includeSubDomains" in value:
                    analysis["strengths"].append("HSTS includes subdomains")
                else:
                    analysis["issues"].append("Consider adding includeSubDomains directive")

                if "preload" in value:
                    analysis["strengths"].append("HSTS preload directive present")

            except (IndexError, ValueError):
                analysis["issues"].append("Invalid HSTS max-age format")
        else:
            analysis["issues"].append("HSTS header missing max-age directive")

        return analysis

    def _analyze_csp(self, value: str) -> Dict[str, Any]:
        """Analyze CSP header."""
        analysis = {"issues": [], "strengths": []}

        # Check for unsafe directives
        if "'unsafe-inline'" in value:
            analysis["issues"].append("CSP contains 'unsafe-inline' directive")
        if "'unsafe-eval'" in value:
            analysis["issues"].append("CSP contains 'unsafe-eval' directive")
        if "*" in value:
            analysis["issues"].append("CSP contains wildcard (*) directive")

        # Check for important directives
        important_directives = ["default-src", "script-src", "style-src", "img-src"]
        present_directives = [directive for directive in important_directives if directive in value]

        if len(present_directives) >= 3:
            analysis["strengths"].append(
                f"Good CSP coverage with {len(present_directives)} important directives"
            )
        else:
            analysis["issues"].append(
                "CSP should include more source directives for better protection"
            )

        return analysis

    def _analyze_frame_options(self, value: str) -> Dict[str, Any]:
        """Analyze X-Frame-Options header."""
        analysis = {"issues": [], "strengths": []}

        value_upper = value.upper()
        if value_upper in ["DENY", "SAMEORIGIN"]:
            analysis["strengths"].append(f"Good X-Frame-Options setting: {value}")
        elif value_upper.startswith("ALLOW-FROM"):
            analysis["issues"].append("ALLOW-FROM is deprecated, use CSP frame-ancestors instead")
        else:
            analysis["issues"].append("Invalid X-Frame-Options value")

        return analysis

    def _analyze_content_type_options(self, value: str) -> Dict[str, Any]:
        """Analyze X-Content-Type-Options header."""
        analysis = {"issues": [], "strengths": []}

        if value.lower() == "nosniff":
            analysis["strengths"].append("Correct X-Content-Type-Options setting")
        else:
            analysis["issues"].append("X-Content-Type-Options should be set to 'nosniff'")

        return analysis

    def _analyze_referrer_policy(self, value: str) -> Dict[str, Any]:
        """Analyze Referrer-Policy header."""
        analysis = {"issues": [], "strengths": []}

        safe_policies = [
            "no-referrer",
            "no-referrer-when-downgrade",
            "strict-origin",
            "strict-origin-when-cross-origin",
        ]

        if value.lower() in safe_policies:
            analysis["strengths"].append(f"Good referrer policy: {value}")
        else:
            analysis["issues"].append("Consider using a more restrictive referrer policy")

        return analysis

    def _analyze_xss_protection(self, value: str) -> Dict[str, Any]:
        """Analyze X-XSS-Protection header."""
        analysis = {"issues": [], "strengths": []}

        if value == "1; mode=block":
            analysis["strengths"].append("Good X-XSS-Protection setting")
        elif value == "0":
            analysis["issues"].append("X-XSS-Protection is disabled")
        else:
            analysis["issues"].append("X-XSS-Protection should be '1; mode=block'")

        analysis["issues"].append("Note: X-XSS-Protection is legacy, CSP is preferred")
        return analysis

    def _calculate_security_score(self, headers_analysis: Dict[str, Any]) -> float:
        """Calculate overall security score (0-100)."""
        total_points = 0
        max_points = 0

        severity_weights = {"high": 30, "medium": 20, "low": 10}

        for header_key, analysis in headers_analysis.items():
            severity = analysis.get("severity", "low")
            weight = severity_weights.get(severity, 10)
            max_points += weight

            if analysis.get("present"):
                # Award points based on presence and quality
                points = weight

                # Reduce points for issues
                header_analysis = analysis.get("analysis", {})
                issues = len(header_analysis.get("issues", []))
                if issues > 0:
                    # Reduce but don't go below 30%
                    points *= max(0.3, 1 - (issues * 0.2))

                total_points += points

        return round((total_points / max_points) * 100, 1) if max_points > 0 else 0

    def _get_security_grade(self, score: float) -> str:
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
