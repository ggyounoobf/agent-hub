"""
SSL/TLS configuration analysis.
"""

import socket
import ssl
from datetime import datetime, timezone
from typing import Any, Dict, List

from shared.utils.logging import logger

# logger = setup_tool_logger('security.ssl')


class SSLAnalyzer:
    """Analyze SSL/TLS configuration and certificates."""

    def __init__(self):
        self.timeout = 30

        # Weak cipher suites to check for
        self.weak_ciphers = {"RC4", "DES", "3DES", "MD5", "SHA1", "NULL", "aNULL", "eNULL"}

        # Strong protocols
        self.strong_protocols = {"TLSv1.2", "TLSv1.3"}

        # Weak protocols
        self.weak_protocols = {"SSLv2", "SSLv3", "TLSv1.0", "TLSv1.1"}

    async def analyze_ssl_config(self, domain: str, port: int = 443) -> Dict[str, Any]:
        """
        Analyze SSL/TLS configuration for a domain.

        Args:
            domain: Domain to analyze
            port: Port to check (default: 443)

        Returns:
            Dictionary with SSL analysis results
        """
        try:
            logger.info(f"Starting SSL analysis for: {domain}:{port}")

            # Get certificate info
            cert_info = await self._get_certificate_info(domain, port)
            if not cert_info.get("success"):
                return cert_info

            # Analyze certificate
            cert_analysis = self._analyze_certificate(cert_info["certificate"])

            # Check protocol support
            protocol_analysis = await self._check_protocol_support(domain, port)

            # Calculate SSL score
            ssl_score = self._calculate_ssl_score(cert_analysis, protocol_analysis)

            return {
                "success": True,
                "domain": domain,
                "port": port,
                "ssl_score": ssl_score,
                "grade": self._get_ssl_grade(ssl_score),
                "certificate_analysis": cert_analysis,
                "protocol_analysis": protocol_analysis,
                "recommendations": self._generate_ssl_recommendations(
                    cert_analysis, protocol_analysis
                ),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error analyzing SSL for {domain}:{port}: {e}")
            return {"success": False, "error": str(e)}

    async def _get_certificate_info(self, domain: str, port: int) -> Dict[str, Any]:
        """Get SSL certificate information."""
        try:
            # Create SSL context
            context = ssl.create_default_context()

            # Connect and get certificate
            with socket.create_connection((domain, port), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert_info = ssock.getpeercert()
                    cipher = ssock.cipher()
                    protocol = ssock.version()

                    return {
                        "success": True,
                        "certificate": cert_info,
                        "cipher": cipher,
                        "protocol": protocol,
                        "connection_details": {
                            "cipher_name": cipher[0] if cipher else None,
                            "cipher_version": cipher[1] if cipher else None,
                            "cipher_bits": cipher[2] if cipher else None,
                            "protocol_version": protocol,
                        },
                    }

        except socket.timeout:
            return {"success": False, "error": "Connection timeout"}
        except socket.gaierror as e:
            return {"success": False, "error": f"DNS resolution failed: {e}"}
        except ssl.SSLError as e:
            return {"success": False, "error": f"SSL error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Connection error: {e}"}

    def _analyze_certificate(self, cert_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze SSL certificate details."""
        analysis = {"issues": [], "strengths": [], "certificate_details": {}}

        # Extract certificate details
        subject = dict(x[0] for x in cert_info.get("subject", []))
        issuer = dict(x[0] for x in cert_info.get("issuer", []))

        analysis["certificate_details"] = {
            "subject": subject,
            "issuer": issuer,
            "version": cert_info.get("version"),
            "serial_number": cert_info.get("serialNumber"),
            "signature_algorithm": cert_info.get("signatureAlgorithm"),
        }

        # Check validity period
        not_before = cert_info.get("notBefore")
        not_after = cert_info.get("notAfter")

        if not_before and not_after:
            try:
                not_before_dt = datetime.strptime(not_before, "%b %d %H:%M:%S %Y %Z")
                not_after_dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                now = datetime.now()

                analysis["certificate_details"]["not_before"] = not_before
                analysis["certificate_details"]["not_after"] = not_after
                analysis["certificate_details"]["is_valid"] = not_before_dt <= now <= not_after_dt

                # Check expiration
                days_until_expiry = (not_after_dt - now).days
                analysis["certificate_details"]["days_until_expiry"] = days_until_expiry

                if days_until_expiry < 0:
                    analysis["issues"].append("Certificate has expired")
                elif days_until_expiry < 30:
                    analysis["issues"].append(
                        f"Certificate expires soon ({days_until_expiry} days)"
                    )
                elif days_until_expiry < 90:
                    analysis["issues"].append(f"Certificate expires in {days_until_expiry} days")
                else:
                    analysis["strengths"].append(f"Certificate valid for {days_until_expiry} days")

            except ValueError as e:
                analysis["issues"].append(f"Invalid certificate date format: {e}")

        # Check signature algorithm
        sig_alg = cert_info.get("signatureAlgorithm", "").lower()
        if "sha1" in sig_alg:
            analysis["issues"].append("Certificate uses weak SHA-1 signature algorithm")
        elif "sha256" in sig_alg or "sha384" in sig_alg or "sha512" in sig_alg:
            analysis["strengths"].append(f"Certificate uses strong signature algorithm: {sig_alg}")

        # Check subject alternative names
        san_list = []
        for ext in cert_info.get("subjectAltName", []):
            if ext[0] == "DNS":
                san_list.append(ext[1])

        analysis["certificate_details"]["subject_alt_names"] = san_list
        if san_list:
            analysis["strengths"].append(
                f"Certificate includes {len(san_list)} Subject Alternative Names"
            )

        return analysis

    async def _check_protocol_support(self, domain: str, port: int) -> Dict[str, Any]:
        """Check supported SSL/TLS protocols."""
        supported_protocols = []
        issues = []
        strengths = []

        # Test current connection protocol
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, port), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    current_protocol = ssock.version()
                    current_cipher = ssock.cipher()

                    supported_protocols.append(
                        {
                            "protocol": current_protocol,
                            "supported": True,
                            "cipher": current_cipher[0] if current_cipher else None,
                            "is_current": True,
                        }
                    )

                    if current_protocol in self.strong_protocols:
                        strengths.append(f"Uses strong protocol: {current_protocol}")
                    elif current_protocol in self.weak_protocols:
                        issues.append(f"Uses weak protocol: {current_protocol}")

                    # Check cipher strength
                    if current_cipher:
                        cipher_name = current_cipher[0].upper()
                        if any(weak in cipher_name for weak in self.weak_ciphers):
                            issues.append(f"Uses weak cipher: {cipher_name}")
                        else:
                            strengths.append(f"Uses strong cipher: {cipher_name}")

        except Exception as e:
            issues.append(f"Could not determine protocol support: {e}")

        # Test for specific protocol versions (simplified approach)
        test_protocols = ["TLSv1.3", "TLSv1.2", "TLSv1.1", "TLSv1.0"]

        for protocol_name in test_protocols:
            # Skip if we already tested this protocol
            if any(p.get("protocol") == protocol_name for p in supported_protocols):
                continue

            try:
                context = ssl.create_default_context()
                # Try to set minimum version (this is a simplified test)
                if hasattr(ssl, "TLSVersion"):
                    try:
                        version_attr = protocol_name.replace(".", "v")
                        if hasattr(ssl.TLSVersion, version_attr):
                            min_version = getattr(ssl.TLSVersion, version_attr)
                            context.minimum_version = min_version
                            context.maximum_version = min_version

                            with socket.create_connection((domain, port), timeout=5) as sock:
                                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                                    cipher_info = ssock.cipher()
                                    supported_protocols.append(
                                        {
                                            "protocol": protocol_name,
                                            "supported": True,
                                            "cipher": (
                                                cipher_info[0] if cipher_info else None
                                            ),  # Fixed: check cipher_info is not None
                                            "is_current": False,
                                        }
                                    )
                                    continue
                    except BaseException:
                        pass

                # Fallback: just record as not supported
                supported_protocols.append(
                    {
                        "protocol": protocol_name,
                        "supported": False,
                        "cipher": None,
                        "is_current": False,
                    }
                )

            except BaseException:
                supported_protocols.append(
                    {
                        "protocol": protocol_name,
                        "supported": False,
                        "cipher": None,
                        "is_current": False,
                    }
                )

        return {
            "supported_protocols": supported_protocols,
            "issues": issues,
            "strengths": strengths,
        }

    def _calculate_ssl_score(
        self, cert_analysis: Dict[str, Any], protocol_analysis: Dict[str, Any]
    ) -> float:
        """Calculate overall SSL score (0-100)."""
        score = 100.0

        # Deduct points for certificate issues
        cert_issues = len(cert_analysis.get("issues", []))
        score -= cert_issues * 15  # 15 points per certificate issue

        # Deduct points for protocol issues
        protocol_issues = len(protocol_analysis.get("issues", []))
        score -= protocol_issues * 10  # 10 points per protocol issue

        # Check if TLS 1.3 is supported (bonus points)
        tls13_supported = any(
            p.get("protocol") == "TLSv1.3" and p.get("supported")
            for p in protocol_analysis.get("supported_protocols", [])
        )
        if tls13_supported:
            score += 5  # Bonus for TLS 1.3

        # Ensure score is within bounds
        return max(0.0, min(100.0, round(score, 1)))

    def _get_ssl_grade(self, score: float) -> str:
        """Convert SSL score to letter grade."""
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

    def _generate_ssl_recommendations(
        self, cert_analysis: Dict[str, Any], protocol_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate SSL configuration recommendations."""
        recommendations = []

        # Certificate recommendations
        cert_issues = cert_analysis.get("issues", [])
        for issue in cert_issues:
            if "expires" in issue.lower():
                recommendations.append("Renew SSL certificate before expiration")
            elif "sha-1" in issue.lower():
                recommendations.append("Upgrade to SHA-256 or higher signature algorithm")

        # Protocol recommendations
        protocol_issues = protocol_analysis.get("issues", [])
        for issue in protocol_issues:
            if "weak protocol" in issue.lower():
                recommendations.append("Disable weak SSL/TLS protocols (SSLv3, TLS 1.0, TLS 1.1)")
            elif "weak cipher" in issue.lower():
                recommendations.append("Configure stronger cipher suites")

        # Check for TLS 1.3 support
        tls13_supported = any(
            p.get("protocol") == "TLSv1.3" and p.get("supported")
            for p in protocol_analysis.get("supported_protocols", [])
        )
        if not tls13_supported:
            recommendations.append("Enable TLS 1.3 support for improved security and performance")

        # General recommendations
        if not recommendations:
            recommendations.append("SSL configuration looks good! Consider regular security audits")

        return recommendations
