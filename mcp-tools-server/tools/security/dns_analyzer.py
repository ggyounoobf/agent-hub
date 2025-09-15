"""
DNS security analysis for domain security assessment.
"""

import asyncio
import socket
from typing import Any, Dict, List
from urllib.parse import urlparse

import aiohttp

from shared.utils.logging import logger

# logger = setup_tool_logger('security.dns')


class DNSSecurityAnalyzer:
    """Analyze DNS configuration for security issues."""

    def __init__(self):
        self.timeout = 30

        # DNS record types to analyze
        self.security_records = {
            "SPF": {"description": "Sender Policy Framework", "severity": "medium"},
            "DMARC": {"description": "Domain-based Message Authentication", "severity": "high"},
            "DKIM": {"description": "DomainKeys Identified Mail", "severity": "medium"},
            "CAA": {"description": "Certificate Authority Authorization", "severity": "medium"},
            "MX": {"description": "Mail Exchange records", "severity": "low"},
            "DNSSEC": {"description": "DNS Security Extensions", "severity": "high"},
        }

        # Common subdomain patterns for discovery
        self.common_subdomains = [
            "www",
            "mail",
            "ftp",
            "admin",
            "api",
            "dev",
            "test",
            "staging",
            "blog",
            "shop",
            "secure",
            "vpn",
            "remote",
            "mx",
            "ns1",
            "ns2",
        ]

        # Dangerous/exposed services to check
        self.dangerous_ports = {
            21: "FTP",
            22: "SSH",
            23: "Telnet",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            110: "POP3",
            143: "IMAP",
            443: "HTTPS",
            993: "IMAPS",
            995: "POP3S",
            3389: "RDP",
            5432: "PostgreSQL",
            3306: "MySQL",
        }

    async def analyze_dns_security(
        self, domain: str, include_subdomains: bool = False, check_email_security: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive DNS security analysis.

        Args:
            domain: Domain to analyze
            include_subdomains: Whether to check common subdomains
            check_email_security: Whether to check email security records

        Returns:
            Dictionary with DNS security analysis results
        """
        try:
            logger.info(f"Starting DNS security analysis for: {domain}")

            # Clean domain name
            domain = self._clean_domain(domain)

            # Basic DNS records analysis
            dns_records = await self._get_dns_records(domain)

            # DNSSEC analysis
            dnssec_status = await self._check_dnssec(domain)

            # Email security analysis
            email_security = {}
            if check_email_security:
                email_security = await self._analyze_email_security(domain)

            # CAA records analysis
            caa_analysis = await self._analyze_caa_records(domain)

            # Subdomain discovery
            subdomains = {}
            if include_subdomains:
                subdomains = await self._discover_subdomains(domain)

            # Calculate DNS security score
            dns_score = self._calculate_dns_score(
                dns_records, dnssec_status, email_security, caa_analysis
            )

            # Generate recommendations
            recommendations = self._generate_dns_recommendations(
                dns_records, dnssec_status, email_security, caa_analysis
            )

            return {
                "success": True,
                "domain": domain,
                "dns_security_score": dns_score,
                "grade": self._get_dns_grade(dns_score),
                "dns_records": dns_records,
                "dnssec_status": dnssec_status,
                "email_security": email_security,
                "caa_analysis": caa_analysis,
                "subdomains": subdomains if include_subdomains else None,
                "recommendations": recommendations,
                "analysis_timestamp": asyncio.get_event_loop().time(),
            }

        except Exception as e:
            logger.error(f"Error analyzing DNS security for {domain}: {e}")
            return {"success": False, "error": str(e)}

    def _clean_domain(self, domain: str) -> str:
        """Clean and normalize domain name."""
        if domain.startswith(("http://", "https://")):
            parsed = urlparse(domain)
            domain = parsed.netloc or parsed.path

        # Remove www prefix if present
        if domain.startswith("www."):
            domain = domain[4:]

        # Remove trailing dot
        if domain.endswith("."):
            domain = domain[:-1]

        return domain.lower()

    async def _get_dns_records(self, domain: str) -> Dict[str, Any]:
        """Get basic DNS records for the domain."""
        records = {"A": [], "AAAA": [], "MX": [], "NS": [], "TXT": [], "CNAME": []}

        record_types = {"A": socket.AF_INET, "AAAA": socket.AF_INET6}

        # Get A and AAAA records
        for record_type, family in record_types.items():
            try:
                result = socket.getaddrinfo(domain, None, family)
                ips = list(set([r[4][0] for r in result]))
                records[record_type] = ips
            except socket.gaierror:
                records[record_type] = []

        # For other record types, we'd need a DNS library like dnspython
        # For now, we'll use a simplified approach or external API
        try:
            await self._get_advanced_dns_records(domain, records)
        except Exception as e:
            logger.warning(f"Could not get advanced DNS records for {domain}: {e}")

        return records

    async def _get_advanced_dns_records(self, domain: str, records: Dict[str, List]) -> None:
        """Get advanced DNS records using external DNS API or library."""
        try:
            # Using a simple DNS-over-HTTPS query to Cloudflare
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:

                # Query MX records
                async with session.get(
                    f"https://cloudflare-dns.com/dns-query?name={domain}&type=MX",
                    headers={"Accept": "application/dns-json"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        mx_records = []
                        for answer in data.get("Answer", []):
                            if answer.get("type") == 15:  # MX record type
                                mx_data = answer.get("data", "").split()
                                if len(mx_data) >= 2:
                                    priority = mx_data[0]
                                    server = mx_data[1].rstrip(".")
                                    mx_records.append(f"{priority} {server}")
                        records["MX"] = mx_records

                # Query TXT records
                async with session.get(
                    f"https://cloudflare-dns.com/dns-query?name={domain}&type=TXT",
                    headers={"Accept": "application/dns-json"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        txt_records = []
                        for answer in data.get("Answer", []):
                            if answer.get("type") == 16:  # TXT record type
                                txt_data = answer.get("data", "").strip('"')
                                txt_records.append(txt_data)
                        records["TXT"] = txt_records

                # Query NS records
                async with session.get(
                    f"https://cloudflare-dns.com/dns-query?name={domain}&type=NS",
                    headers={"Accept": "application/dns-json"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        ns_records = []
                        for answer in data.get("Answer", []):
                            if answer.get("type") == 2:  # NS record type
                                ns_data = answer.get("data", "").rstrip(".")
                                ns_records.append(ns_data)
                        records["NS"] = ns_records

                # Query CAA records
                async with session.get(
                    f"https://cloudflare-dns.com/dns-query?name={domain}&type=CAA",
                    headers={"Accept": "application/dns-json"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        caa_records = []
                        for answer in data.get("Answer", []):
                            if answer.get("type") == 257:  # CAA record type
                                caa_records.append(answer.get("data", ""))
                        records["CAA"] = caa_records

        except Exception as e:
            logger.warning(f"Failed to get advanced DNS records: {e}")

    async def _check_dnssec(self, domain: str) -> Dict[str, Any]:
        """Check DNSSEC status for the domain."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                # Query DNSKEY records to check DNSSEC
                async with session.get(
                    f"https://cloudflare-dns.com/dns-query?name={domain}&type=DNSKEY",
                    headers={"Accept": "application/dns-json"},
                ) as response:

                    if response.status == 200:
                        data = await response.json()
                        has_dnskey = len(data.get("Answer", [])) > 0

                        return {
                            "enabled": has_dnskey,
                            "status": "Enabled" if has_dnskey else "Disabled",
                            "records_found": len(data.get("Answer", [])),
                            "details": data.get("Answer", []) if has_dnskey else None,
                        }
                    else:
                        return {
                            "enabled": False,
                            "status": "Unable to determine",
                            "error": f"DNS query failed with status {response.status}",
                        }

        except Exception as e:
            logger.warning(f"DNSSEC check failed for {domain}: {e}")
            return {"enabled": False, "status": "Check failed", "error": str(e)}

    async def _analyze_email_security(self, domain: str) -> Dict[str, Any]:
        """Analyze email security records (SPF, DMARC, DKIM)."""
        email_security = {
            "spf": {"present": False, "record": None, "analysis": {}},
            "dmarc": {"present": False, "record": None, "analysis": {}},
            "dkim": {"present": False, "selectors_found": [], "analysis": {}},
        }

        try:
            # Get TXT records for SPF and DMARC analysis
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:

                # Check SPF record
                async with session.get(
                    f"https://cloudflare-dns.com/dns-query?name={domain}&type=TXT",
                    headers={"Accept": "application/dns-json"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        for answer in data.get("Answer", []):
                            if answer.get("type") == 16:  # TXT record
                                txt_data = answer.get("data", "").strip('"')

                                # Check for SPF record
                                if txt_data.startswith("v=spf1"):
                                    email_security["spf"]["present"] = True
                                    email_security["spf"]["record"] = txt_data
                                    email_security["spf"]["analysis"] = self._analyze_spf_record(
                                        txt_data
                                    )

                # Check DMARC record
                dmarc_domain = f"_dmarc.{domain}"
                async with session.get(
                    f"https://cloudflare-dns.com/dns-query?name={dmarc_domain}&type=TXT",
                    headers={"Accept": "application/dns-json"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        for answer in data.get("Answer", []):
                            if answer.get("type") == 16:  # TXT record
                                txt_data = answer.get("data", "").strip('"')

                                # Check for DMARC record
                                if txt_data.startswith("v=DMARC1"):
                                    email_security["dmarc"]["present"] = True
                                    email_security["dmarc"]["record"] = txt_data
                                    email_security["dmarc"]["analysis"] = (
                                        self._analyze_dmarc_record(txt_data)
                                    )

                # Check common DKIM selectors
                common_selectors = ["default", "selector1", "selector2", "google", "k1", "dkim"]
                for selector in common_selectors:
                    dkim_domain = f"{selector}._domainkey.{domain}"
                    try:
                        async with session.get(
                            f"https://cloudflare-dns.com/dns-query?name={dkim_domain}&type=TXT",
                            headers={"Accept": "application/dns-json"},
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                if data.get("Answer"):
                                    email_security["dkim"]["present"] = True
                                    email_security["dkim"]["selectors_found"].append(selector)
                    except BaseException:
                        continue  # Selector not found, continue to next

        except Exception as e:
            logger.warning(f"Email security analysis failed for {domain}: {e}")

        return email_security

    def _analyze_spf_record(self, spf_record: str) -> Dict[str, Any]:
        """Analyze SPF record for security issues."""
        analysis = {"issues": [], "strengths": [], "mechanisms": []}

        # Parse SPF mechanisms
        parts = spf_record.split()
        for part in parts[1:]:  # Skip 'v=spf1'
            if part.startswith(("include:", "a:", "mx:", "ip4:", "ip6:", "exists:")):
                analysis["mechanisms"].append(part)
            elif part in ["+all", "?all", "~all", "-all"]:
                analysis["mechanisms"].append(part)

                # Analyze all mechanism
                if part == "+all":
                    analysis["issues"].append(
                        "SPF record allows all senders (+all) - very permissive"
                    )
                elif part == "?all":
                    analysis["issues"].append(
                        "SPF record is neutral (?all) - provides limited protection"
                    )
                elif part == "~all":
                    analysis["strengths"].append("SPF record has soft fail (~all) - good practice")
                elif part == "-all":
                    analysis["strengths"].append("SPF record has hard fail (-all) - strict policy")

        # Check for too many DNS lookups (SPF has 10 lookup limit)
        lookup_mechanisms = [
            m for m in analysis["mechanisms"] if m.startswith(("include:", "a:", "mx:", "exists:"))
        ]
        if len(lookup_mechanisms) > 8:
            analysis["issues"].append(
                f"SPF record may exceed 10 DNS lookup limit ({len(lookup_mechanisms)} lookups)"
            )

        return analysis

    def _analyze_dmarc_record(self, dmarc_record: str) -> Dict[str, Any]:
        """Analyze DMARC record for security issues."""
        analysis = {"issues": [], "strengths": [], "policies": {}}

        # Parse DMARC tags
        parts = dmarc_record.split(";")
        for part in parts:
            if "=" in part:
                key, value = part.strip().split("=", 1)
                analysis["policies"][key] = value

        # Analyze policy
        policy = analysis["policies"].get("p", "")
        if policy == "none":
            analysis["issues"].append("DMARC policy is 'none' - monitoring only, no enforcement")
        elif policy == "quarantine":
            analysis["strengths"].append(
                "DMARC policy set to 'quarantine' - suspicious emails quarantined"
            )
        elif policy == "reject":
            analysis["strengths"].append(
                "DMARC policy set to 'reject' - strongest DMARC protection"
            )

        # Check subdomain policy
        sp = analysis["policies"].get("sp", "")
        if sp:
            analysis["strengths"].append(f"Subdomain policy specified: {sp}")
        else:
            analysis["issues"].append("No subdomain policy specified - inherits main domain policy")

        # Check percentage
        pct = analysis["policies"].get("pct", "100")
        if pct != "100":
            analysis["issues"].append(
                f"DMARC enforcement percentage is {pct}% - not fully enforced"
            )

        return analysis

    async def _analyze_caa_records(self, domain: str) -> Dict[str, Any]:
        """Analyze Certificate Authority Authorization records."""
        caa_analysis = {
            "present": False,
            "records": [],
            "authorized_cas": [],
            "analysis": {"issues": [], "strengths": []},
        }

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(
                    f"https://cloudflare-dns.com/dns-query?name={domain}&type=CAA",
                    headers={"Accept": "application/dns-json"},
                ) as response:

                    if response.status == 200:
                        data = await response.json()
                        caa_records = []

                        for answer in data.get("Answer", []):
                            if answer.get("type") == 257:  # CAA record type
                                caa_records.append(answer.get("data", ""))

                        if caa_records:
                            caa_analysis["present"] = True
                            caa_analysis["records"] = caa_records
                            caa_analysis["analysis"]["strengths"].append(
                                "CAA records present - restricts certificate issuance"
                            )

                            # Parse CAA records to extract authorized CAs
                            for record in caa_records:
                                parts = record.split('"')
                                if len(parts) >= 2:
                                    ca_domain = parts[1]
                                    caa_analysis["authorized_cas"].append(ca_domain)
                        else:
                            caa_analysis["analysis"]["issues"].append(
                                "No CAA records found - any CA can issue certificates"
                            )

        except Exception as e:
            logger.warning(f"CAA analysis failed for {domain}: {e}")
            caa_analysis["analysis"]["issues"].append("Failed to check CAA records")

        return caa_analysis

    async def _discover_subdomains(self, domain: str, max_concurrent: int = 10) -> Dict[str, Any]:
        """Discover common subdomains (non-invasive enumeration)."""
        subdomains_found = []

        semaphore = asyncio.Semaphore(max_concurrent)

        async def check_subdomain(subdomain):
            async with semaphore:
                full_domain = f"{subdomain}.{domain}"
                try:
                    # Simple DNS lookup
                    result = socket.getaddrinfo(full_domain, None)
                    if result:
                        ips = list(set([r[4][0] for r in result]))
                        return {"subdomain": full_domain, "found": True, "ips": ips}
                except socket.gaierror:
                    pass

                return {"subdomain": full_domain, "found": False}

        # Check common subdomains
        tasks = [check_subdomain(sub) for sub in self.common_subdomains]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, dict) and result.get("found"):
                subdomains_found.append(result)

        return {
            "total_checked": len(self.common_subdomains),
            "found_count": len(subdomains_found),
            "subdomains": subdomains_found,
        }

    def _calculate_dns_score(
        self, dns_records: Dict, dnssec_status: Dict, email_security: Dict, caa_analysis: Dict
    ) -> float:
        """Calculate overall DNS security score."""
        score = 100.0

        # DNSSEC (30 points)
        if not dnssec_status.get("enabled"):
            score -= 30

        # Email security (40 points total)
        # SPF (15 points)
        if not email_security.get("spf", {}).get("present"):
            score -= 15
        else:
            spf_issues = len(email_security["spf"]["analysis"].get("issues", []))
            score -= spf_issues * 3  # 3 points per SPF issue

        # DMARC (20 points)
        if not email_security.get("dmarc", {}).get("present"):
            score -= 20
        else:
            dmarc_policy = email_security["dmarc"]["analysis"]["policies"].get("p", "")
            if dmarc_policy == "none":
                score -= 10  # Partial credit for having DMARC but not enforcing
            elif dmarc_policy not in ["quarantine", "reject"]:
                score -= 15

        # DKIM (5 points)
        if not email_security.get("dkim", {}).get("present"):
            score -= 5

        # CAA records (10 points)
        if not caa_analysis.get("present"):
            score -= 10

        # Basic DNS hygiene (15 points)
        if not dns_records.get("A") and not dns_records.get("AAAA"):
            score -= 15  # No A or AAAA records

        return max(0.0, min(100.0, round(score, 1)))

    def _get_dns_grade(self, score: float) -> str:
        """Convert DNS security score to letter grade."""
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

    def _generate_dns_recommendations(
        self, dns_records: Dict, dnssec_status: Dict, email_security: Dict, caa_analysis: Dict
    ) -> List[str]:
        """Generate DNS security recommendations."""
        recommendations = []

        # DNSSEC recommendations
        if not dnssec_status.get("enabled"):
            recommendations.append(
                "Enable DNSSEC to protect against DNS spoofing and cache poisoning"
            )

        # Email security recommendations
        if not email_security.get("spf", {}).get("present"):
            recommendations.append("Implement SPF record to specify authorized mail servers")
        else:
            spf_issues = email_security["spf"]["analysis"].get("issues", [])
            recommendations.extend([f"SPF: {issue}" for issue in spf_issues])

        if not email_security.get("dmarc", {}).get("present"):
            recommendations.append("Implement DMARC policy for email authentication and reporting")
        else:
            dmarc_issues = email_security["dmarc"]["analysis"].get("issues", [])
            recommendations.extend([f"DMARC: {issue}" for issue in dmarc_issues])

        if not email_security.get("dkim", {}).get("present"):
            recommendations.append("Configure DKIM signing for email authentication")

        # CAA recommendations
        if not caa_analysis.get("present"):
            recommendations.append(
                "Add CAA records to restrict which Certificate Authorities can issue certificates"
            )

        # General recommendations
        if not recommendations:
            recommendations.append(
                "DNS security configuration looks good! Consider regular monitoring"
            )

        return recommendations[:10]  # Limit to top 10 recommendations
