"""
Safe security scanner that orchestrates comprehensive security analysis.
Performs non-invasive security assessments using multiple analysis engines.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from shared.utils.logging import logger

from .dns_analyzer import DNSSecurityAnalyzer
from .header_analyzer import SecurityHeaderAnalyzer
from .report_generator import SecurityReportGenerator
from .ssl_analyzer import SSLAnalyzer

# logger = setup_tool_logger('security.safe_scanner')


class SafeSecurityScanner:
    """
    Safe security scanner that performs comprehensive non-invasive security assessments.
    Coordinates multiple analysis engines to provide complete security evaluation.
    """

    def __init__(self):
        # Initialize analysis engines
        self.header_analyzer = SecurityHeaderAnalyzer()
        self.ssl_analyzer = SSLAnalyzer()
        self.dns_analyzer = DNSSecurityAnalyzer()
        self.report_generator = SecurityReportGenerator()

        # Scanner configuration
        self.max_concurrent_scans = 5
        self.timeout_per_analysis = 60  # seconds
        self.retry_attempts = 2

        # Analysis weights for overall scoring
        self.analysis_weights = {
            "headers": 0.3,  # 30% weight
            "ssl_tls": 0.4,  # 40% weight
            "dns": 0.3,  # 30% weight
        }

        # Scan profiles
        self.scan_profiles = {
            "quick": {
                "include_headers": True,
                "include_ssl": True,
                "include_dns": False,
                "include_subdomains": False,
                "check_email_security": False,
                "description": "Quick security headers and SSL check",
            },
            "standard": {
                "include_headers": True,
                "include_ssl": True,
                "include_dns": True,
                "include_subdomains": False,
                "check_email_security": True,
                "description": "Standard security assessment",
            },
            "comprehensive": {
                "include_headers": True,
                "include_ssl": True,
                "include_dns": True,
                "include_subdomains": True,
                "check_email_security": True,
                "description": "Comprehensive security analysis",
            },
            "compliance": {
                "include_headers": True,
                "include_ssl": True,
                "include_dns": True,
                "include_subdomains": False,
                "check_email_security": True,
                "description": "Compliance-focused assessment",
            },
        }

    async def scan_target(
        self,
        target: str,
        scan_profile: str = "standard",
        custom_options: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, Any]:
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
            logger.info(f"Starting safe security scan for target: {target}")
            start_time = time.time()

            # Validate and normalize target
            normalized_target = self._normalize_target(target)
            if not normalized_target["success"]:
                return normalized_target

            url = normalized_target["url"]
            domain = normalized_target["domain"]

            # Get scan configuration
            scan_config = self._get_scan_configuration(scan_profile, custom_options)

            # Perform security analyses
            analysis_results = await self._perform_security_analyses(url, domain, scan_config)

            # Calculate overall security score
            overall_score = self._calculate_overall_score(analysis_results)

            # Generate security recommendations
            recommendations = self._generate_comprehensive_recommendations(analysis_results)

            # Assess security posture
            security_posture = self._assess_security_posture(analysis_results, overall_score)

            # Calculate scan duration
            scan_duration = round(time.time() - start_time, 2)

            result = {
                "success": True,
                "target": target,
                "normalized_url": url,
                "domain": domain,
                "scan_profile": scan_profile,
                "scan_configuration": scan_config,
                "overall_security_score": overall_score["score"],
                "overall_grade": overall_score["grade"],
                "security_posture": security_posture,
                "analysis_results": analysis_results,
                "comprehensive_recommendations": recommendations,
                "scan_metadata": {
                    "scan_duration": scan_duration,
                    "analyses_performed": len(
                        [k for k, v in analysis_results.items() if v.get("success")]
                    ),
                    "total_analyses": len(analysis_results),
                    "scan_timestamp": time.time(),
                    "scanner_version": "1.0.0",
                },
            }

            logger.info(f"Security scan completed for {target} in {scan_duration}s")
            return result

        except Exception as e:
            logger.error(f"Error during security scan of {target}: {e}")
            return {
                "success": False,
                "target": target,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    async def batch_scan_targets(
        self,
        targets: List[str],
        scan_profile: str = "standard",
        max_concurrent: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Perform security scans on multiple targets concurrently.

        Args:
            targets: List of targets to scan
            scan_profile: Scan profile to use for all targets
            max_concurrent: Maximum concurrent scans (overrides default)

        Returns:
            Dictionary with batch scan results
        """
        try:
            logger.info(f"Starting batch security scan for {len(targets)} targets")
            start_time = time.time()

            # Validate targets
            if not targets or len(targets) == 0:
                return {"success": False, "error": "No targets provided for scanning"}

            # Set concurrency limit
            concurrent_limit = min(
                max_concurrent or self.max_concurrent_scans,
                len(targets),
                10,  # Hard limit for safety
            )

            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(concurrent_limit)

            async def scan_single_target(target):
                async with semaphore:
                    return await self.scan_target(target, scan_profile)

            # Execute scans concurrently
            scan_tasks = [scan_single_target(target) for target in targets]
            scan_results = await asyncio.gather(*scan_tasks, return_exceptions=True)

            # Process results
            successful_scans = []
            failed_scans = []

            for i, result in enumerate(scan_results):
                target = targets[i]

                if isinstance(result, Exception):
                    failed_scans.append(
                        {
                            "target": target,
                            "error": str(result),
                            "error_type": type(result).__name__,
                        }
                    )
                elif isinstance(result, dict) and result.get("success"):  # Added isinstance check
                    successful_scans.append(result)
                else:
                    # Handle case where result is dict but not successful
                    error_msg = "Unknown error"
                    if isinstance(result, dict):
                        error_msg = result.get("error", "Unknown error")

                    failed_scans.append({"target": target, "error": error_msg})

            # Calculate batch statistics
            batch_stats = self._calculate_batch_statistics(successful_scans)

            batch_duration = round(time.time() - start_time, 2)

            return {
                "success": True,
                "batch_summary": {
                    "total_targets": len(targets),
                    "successful_scans": len(successful_scans),
                    "failed_scans": len(failed_scans),
                    "success_rate": round(len(successful_scans) / len(targets) * 100, 1),
                    "batch_duration": batch_duration,
                    "average_scan_time": round(batch_duration / len(targets), 2),
                    "concurrent_limit": concurrent_limit,
                },
                "batch_statistics": batch_stats,
                "successful_results": successful_scans,
                "failed_results": failed_scans,
                "scan_profile_used": scan_profile,
            }

        except Exception as e:
            logger.error(f"Error during batch security scan: {e}")
            return {"success": False, "error": str(e), "targets_attempted": len(targets)}

    async def compare_targets(
        self, targets: List[str], scan_profile: str = "standard"
    ) -> Dict[str, Any]:
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

            # Perform batch scan
            batch_results = await self.batch_scan_targets(targets, scan_profile)

            if not batch_results.get("success"):
                return batch_results

            successful_results = batch_results["successful_results"]

            if len(successful_results) < 2:
                return {
                    "success": False,
                    "error": "Need at least 2 successful scans for comparison",
                }

            # Perform comparison analysis
            comparison = self._perform_comparison_analysis(successful_results)

            return {
                "success": True,
                "comparison_summary": {
                    "targets_compared": len(successful_results),
                    "best_performer": comparison["best_performer"],
                    "worst_performer": comparison["worst_performer"],
                    "average_score": comparison["average_score"],
                    "score_range": comparison["score_range"],
                },
                "detailed_comparison": comparison["detailed_comparison"],
                "security_rankings": comparison["rankings"],
                "common_issues": comparison["common_issues"],
                "improvement_opportunities": comparison["improvement_opportunities"],
                "batch_results": batch_results,
            }

        except Exception as e:
            logger.error(f"Error during target comparison: {e}")
            return {"success": False, "error": str(e)}

    async def continuous_monitoring_scan(
        self, target: str, monitoring_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform continuous monitoring scan with baseline comparison.

        Args:
            target: Target to monitor
            monitoring_config: Monitoring configuration including baseline

        Returns:
            Dictionary with monitoring results and change detection
        """
        try:
            logger.info(f"Starting continuous monitoring scan for: {target}")

            # Perform current scan
            current_scan = await self.scan_target(
                target, monitoring_config.get("scan_profile", "standard")
            )

            if not current_scan.get("success"):
                return current_scan

            # Compare with baseline if provided
            baseline = monitoring_config.get("baseline")
            if baseline:
                change_analysis = self._analyze_security_changes(baseline, current_scan)
            else:
                change_analysis = {
                    "baseline_available": False,
                    "message": "No baseline provided - this scan can serve as baseline",
                }

            # Check thresholds
            threshold_analysis = self._check_monitoring_thresholds(
                current_scan, monitoring_config.get("thresholds", {})
            )

            return {
                "success": True,
                "monitoring_type": "continuous_monitoring",
                "target": target,
                "current_scan": current_scan,
                "change_analysis": change_analysis,
                "threshold_analysis": threshold_analysis,
                "monitoring_metadata": {
                    "monitoring_timestamp": time.time(),
                    "baseline_comparison": baseline is not None,
                    "thresholds_configured": len(monitoring_config.get("thresholds", {})),
                },
            }

        except Exception as e:
            logger.error(f"Error during continuous monitoring scan: {e}")
            return {"success": False, "error": str(e)}

    def _normalize_target(self, target: str) -> Dict[str, Any]:
        """Normalize and validate target URL/domain."""
        try:
            # Add protocol if missing
            if not target.startswith(("http://", "https://")):
                target = "https://" + target

            # Parse URL
            parsed = urlparse(target)

            if not parsed.netloc:
                return {"success": False, "error": "Invalid target format"}

            # Extract domain
            domain = parsed.netloc
            if domain.startswith("www."):
                domain = domain[4:]

            return {
                "success": True,
                "url": target,
                "domain": domain,
                "scheme": parsed.scheme,
                "netloc": parsed.netloc,
            }

        except Exception as e:
            return {"success": False, "error": f"Target normalization failed: {e}"}

    def _get_scan_configuration(
        self, profile: str, custom_options: Optional[Dict[str, bool]]
    ) -> Dict[str, Any]:
        """Get scan configuration based on profile and custom options."""
        if profile not in self.scan_profiles:
            profile = "standard"

        config = self.scan_profiles[profile].copy()

        # Apply custom options if provided
        if custom_options:
            config.update(custom_options)

        return config

    async def _perform_security_analyses(
        self, url: str, domain: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform all configured security analyses."""
        analyses = {}

        # Create analysis tasks based on configuration
        tasks = {}

        if config.get("include_headers", True):
            tasks["headers"] = self._analyze_headers_with_retry(url)

        if config.get("include_ssl", True):
            tasks["ssl_tls"] = self._analyze_ssl_with_retry(domain)

        if config.get("include_dns", True):
            tasks["dns"] = self._analyze_dns_with_retry(
                domain,
                config.get("include_subdomains", False),
                config.get("check_email_security", True),
            )

        # Execute analyses concurrently with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks.values(), return_exceptions=True),
                timeout=self.timeout_per_analysis,
            )

            # Map results back to analysis names
            for i, (analysis_name, _) in enumerate(tasks.items()):
                result = results[i]

                if isinstance(result, Exception):
                    analyses[analysis_name] = {
                        "success": False,
                        "error": str(result),
                        "error_type": type(result).__name__,
                    }
                else:
                    analyses[analysis_name] = result

        except asyncio.TimeoutError:
            logger.warning(f"Security analysis timeout for domain: {domain}")
            for analysis_name in tasks.keys():
                if analysis_name not in analyses:
                    analyses[analysis_name] = {"success": False, "error": "Analysis timeout"}

        return analyses

    async def _analyze_headers_with_retry(self, url: str) -> Dict[str, Any]:
        """Analyze headers with retry logic."""
        for attempt in range(self.retry_attempts + 1):
            try:
                result = await self.header_analyzer.analyze_headers(url)
                if result.get("success"):
                    return result

                if attempt < self.retry_attempts:
                    logger.debug(f"Header analysis retry {attempt + 1} for {url}")
                    # Exponential backoff
                    await asyncio.sleep(1 * (attempt + 1))
                else:
                    return result

            except Exception as e:
                if attempt < self.retry_attempts:
                    logger.debug(f"Header analysis exception retry {attempt + 1} for {url}: {e}")
                    await asyncio.sleep(1 * (attempt + 1))
                else:
                    return {"success": False, "error": str(e)}

        return {"success": False, "error": "Max retries exceeded"}

    async def _analyze_ssl_with_retry(self, domain: str) -> Dict[str, Any]:
        """Analyze SSL with retry logic."""
        for attempt in range(self.retry_attempts + 1):
            try:
                result = await self.ssl_analyzer.analyze_ssl_config(domain)
                if result.get("success"):
                    return result

                if attempt < self.retry_attempts:
                    logger.debug(f"SSL analysis retry {attempt + 1} for {domain}")
                    await asyncio.sleep(1 * (attempt + 1))
                else:
                    return result

            except Exception as e:
                if attempt < self.retry_attempts:
                    logger.debug(f"SSL analysis exception retry {attempt + 1} for {domain}: {e}")
                    await asyncio.sleep(1 * (attempt + 1))
                else:
                    return {"success": False, "error": str(e)}

        return {"success": False, "error": "Max retries exceeded"}

    async def _analyze_dns_with_retry(
        self, domain: str, include_subdomains: bool = False, check_email_security: bool = True
    ) -> Dict[str, Any]:
        """Analyze DNS with retry logic."""
        for attempt in range(self.retry_attempts + 1):
            try:
                result = await self.dns_analyzer.analyze_dns_security(
                    domain, include_subdomains, check_email_security
                )
                if result.get("success"):
                    return result

                if attempt < self.retry_attempts:
                    logger.debug(f"DNS analysis retry {attempt + 1} for {domain}")
                    await asyncio.sleep(1 * (attempt + 1))
                else:
                    return result

            except Exception as e:
                if attempt < self.retry_attempts:
                    logger.debug(f"DNS analysis exception retry {attempt + 1} for {domain}: {e}")
                    await asyncio.sleep(1 * (attempt + 1))
                else:
                    return {"success": False, "error": str(e)}

        return {"success": False, "error": "Max retries exceeded"}

    def _calculate_overall_score(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall security score from individual analyses."""
        total_weighted_score = 0
        total_weight = 0

        score_mapping = {
            "headers": "security_score",
            "ssl_tls": "ssl_score",
            "dns": "dns_security_score",
        }

        for analysis_name, weight in self.analysis_weights.items():
            analysis_result = analysis_results.get(analysis_name, {})

            if analysis_result.get("success"):
                score_key = score_mapping.get(analysis_name)
                if score_key and score_key in analysis_result:
                    score = analysis_result[score_key]
                    total_weighted_score += score * weight
                    total_weight += weight

        if total_weight > 0:
            overall_score = total_weighted_score / total_weight
        else:
            overall_score = 0

        return {
            "score": round(overall_score, 1),
            "grade": self._score_to_grade(overall_score),
            "weight_distribution": {
                k: v for k, v in self.analysis_weights.items() if k in analysis_results
            },
        }

    def _generate_comprehensive_recommendations(
        self, analysis_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive recommendations from all analyses."""
        all_recommendations = []

        # Collect recommendations from each analysis
        for analysis_name, analysis_result in analysis_results.items():
            if analysis_result.get("success") and "recommendations" in analysis_result:
                for rec in analysis_result["recommendations"]:
                    all_recommendations.append(
                        {
                            "category": analysis_name.replace("_", " ").title(),
                            "recommendation": rec,
                            "priority": self._determine_recommendation_priority(rec),
                            "source_analysis": analysis_name,
                        }
                    )

        # Group by priority
        grouped_recommendations = {"critical": [], "high": [], "medium": [], "low": []}

        for rec in all_recommendations:
            priority = rec["priority"]
            if priority in grouped_recommendations:
                grouped_recommendations[priority].append(rec)

        # Get top recommendations overall
        top_recommendations = sorted(
            all_recommendations,
            key=lambda x: {"critical": 1, "high": 2, "medium": 3, "low": 4}.get(x["priority"], 5),
        )[:10]

        return {
            "grouped_by_priority": grouped_recommendations,
            "top_recommendations": top_recommendations,
            "total_recommendations": len(all_recommendations),
            "recommendations_by_category": self._group_recommendations_by_category(
                all_recommendations
            ),
        }

    def _assess_security_posture(
        self, analysis_results: Dict[str, Any], overall_score: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess overall security posture."""
        score = overall_score["score"]

        # Determine risk level
        if score >= 90:
            risk_level = "Very Low"
            posture = "Excellent"
        elif score >= 80:
            risk_level = "Low"
            posture = "Good"
        elif score >= 70:
            risk_level = "Medium"
            posture = "Fair"
        elif score >= 60:
            risk_level = "High"
            posture = "Poor"
        else:
            risk_level = "Critical"
            posture = "Very Poor"

        # Count issues by severity
        critical_issues = 0
        high_issues = 0
        medium_issues = 0

        for analysis_result in analysis_results.values():
            if analysis_result.get("success"):
                # Count missing high-severity headers
                if "missing_headers" in analysis_result:
                    for header in analysis_result["missing_headers"]:
                        if header.get("severity") == "high":
                            critical_issues += 1
                        elif header.get("severity") == "medium":
                            high_issues += 1
                        else:
                            medium_issues += 1

                # Count SSL/TLS issues
                if "certificate_analysis" in analysis_result:
                    cert_issues = len(analysis_result["certificate_analysis"].get("issues", []))
                    if cert_issues > 0:
                        high_issues += cert_issues

                # Count DNS security issues
                if "dnssec_status" in analysis_result:
                    if not analysis_result["dnssec_status"].get("enabled"):
                        high_issues += 1

        return {
            "overall_posture": posture,
            "risk_level": risk_level,
            "security_score": score,
            "security_grade": overall_score["grade"],
            "issue_summary": {
                "critical_issues": critical_issues,
                "high_risk_issues": high_issues,
                "medium_risk_issues": medium_issues,
                "total_issues": critical_issues + high_issues + medium_issues,
            },
            "strengths": self._identify_security_strengths(analysis_results),
            "weaknesses": self._identify_security_weaknesses(analysis_results),
            "compliance_status": self._assess_compliance_readiness(analysis_results),
        }

    def _calculate_batch_statistics(self, successful_scans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics for batch scan results."""
        if not successful_scans:
            return {}

        scores = [scan["overall_security_score"] for scan in successful_scans]

        return {
            "average_security_score": round(sum(scores) / len(scores), 1),
            "highest_score": max(scores),
            "lowest_score": min(scores),
            "score_range": max(scores) - min(scores),
            "grade_distribution": self._calculate_grade_distribution(scores),
            "common_security_issues": self._identify_common_issues(successful_scans),
            "best_practices_adoption": self._calculate_best_practices_adoption(successful_scans),
        }

    def _perform_comparison_analysis(self, scan_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform detailed comparison analysis between targets."""
        # Sort by score
        sorted_results = sorted(
            scan_results, key=lambda x: x["overall_security_score"], reverse=True
        )

        best_performer = sorted_results[0]
        worst_performer = sorted_results[-1]

        scores = [result["overall_security_score"] for result in scan_results]
        average_score = round(sum(scores) / len(scores), 1)

        # Detailed comparison
        detailed_comparison = []
        for result in sorted_results:
            target_comparison = {
                "target": result["target"],
                "overall_score": result["overall_security_score"],
                "overall_grade": result["overall_grade"],
                "rank": sorted_results.index(result) + 1,
                "analysis_breakdown": {},
            }

            # Add analysis breakdown
            analysis_results = result.get("analysis_results", {})
            for analysis_name, analysis_data in analysis_results.items():
                if analysis_data.get("success"):
                    score_key = {
                        "headers": "security_score",
                        "ssl_tls": "ssl_score",
                        "dns": "dns_security_score",
                    }.get(analysis_name)

                    if score_key and score_key in analysis_data:
                        target_comparison["analysis_breakdown"][analysis_name] = {
                            "score": analysis_data[score_key],
                            "grade": analysis_data.get("grade", "F"),
                        }

            detailed_comparison.append(target_comparison)

        # Identify common issues
        common_issues = self._identify_common_issues(scan_results)

        # Improvement opportunities
        improvement_opportunities = self._identify_improvement_opportunities(scan_results)

        return {
            "best_performer": {
                "target": best_performer["target"],
                "score": best_performer["overall_security_score"],
                "grade": best_performer["overall_grade"],
            },
            "worst_performer": {
                "target": worst_performer["target"],
                "score": worst_performer["overall_security_score"],
                "grade": worst_performer["overall_grade"],
            },
            "average_score": average_score,
            "score_range": max(scores) - min(scores),
            "detailed_comparison": detailed_comparison,
            "rankings": [
                {
                    "rank": i + 1,
                    "target": result["target"],
                    "score": result["overall_security_score"],
                    "grade": result["overall_grade"],
                }
                for i, result in enumerate(sorted_results)
            ],
            "common_issues": common_issues,
            "improvement_opportunities": improvement_opportunities,
        }

    def _analyze_security_changes(
        self, baseline: Dict[str, Any], current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze changes between baseline and current scan."""
        baseline_score = baseline.get("overall_security_score", 0)
        current_score = current.get("overall_security_score", 0)

        score_change = current_score - baseline_score

        # Determine change significance
        if abs(score_change) < 2:
            change_significance = "Minimal"
        elif abs(score_change) < 5:
            change_significance = "Minor"
        elif abs(score_change) < 10:
            change_significance = "Moderate"
        else:
            change_significance = "Significant"

        change_direction = (
            "Improved" if score_change > 0 else "Degraded" if score_change < 0 else "Unchanged"
        )

        # Analyze specific changes
        specific_changes = self._detect_specific_changes(baseline, current)

        return {
            "baseline_available": True,
            "score_change": round(score_change, 1),
            "change_direction": change_direction,
            "change_significance": change_significance,
            "baseline_score": baseline_score,
            "current_score": current_score,
            "specific_changes": specific_changes,
            "change_summary": self._generate_change_summary(score_change, specific_changes),
        }

    def _check_monitoring_thresholds(
        self, scan_result: Dict[str, Any], thresholds: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check scan results against monitoring thresholds."""
        threshold_checks = {}
        alerts = []

        # Check score threshold
        min_score = thresholds.get("minimum_security_score", 70)
        current_score = scan_result.get("overall_security_score", 0)

        threshold_checks["security_score"] = {
            "threshold": min_score,
            "current_value": current_score,
            "passed": current_score >= min_score,
            "margin": current_score - min_score,
        }

        if current_score < min_score:
            alerts.append(
                {
                    "type": "security_score_below_threshold",
                    "severity": "high",
                    "message": f"Security score {current_score} below threshold {min_score}",
                    "recommended_action": "Investigate security degradation",
                }
            )

        # Check for critical issues
        max_critical_issues = thresholds.get("max_critical_issues", 0)
        security_posture = scan_result.get("security_posture", {})
        critical_issues = security_posture.get("issue_summary", {}).get("critical_issues", 0)

        threshold_checks["critical_issues"] = {
            "threshold": max_critical_issues,
            "current_value": critical_issues,
            "passed": critical_issues <= max_critical_issues,
        }

        if critical_issues > max_critical_issues:
            alerts.append(
                {
                    "type": "critical_issues_threshold_exceeded",
                    "severity": "critical",
                    "message": f"Found {critical_issues} critical issues (threshold: {max_critical_issues})",
                    "recommended_action": "Address critical security issues immediately",
                }
            )

        return {
            "threshold_checks": threshold_checks,
            "alerts": alerts,
            "overall_status": "PASS" if len(alerts) == 0 else "FAIL",
            "total_alerts": len(alerts),
        }

    # Helper methods
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

    def _determine_recommendation_priority(self, recommendation: str) -> str:
        """Determine priority level of a recommendation."""
        critical_keywords = ["expired", "critical", "immediately", "urgent", "vulnerability"]
        high_keywords = ["missing", "implement", "enable", "vulnerable", "weak"]
        medium_keywords = ["improve", "upgrade", "consider", "enhance", "should"]

        rec_lower = recommendation.lower()

        if any(keyword in rec_lower for keyword in critical_keywords):
            return "critical"
        elif any(keyword in rec_lower for keyword in high_keywords):
            return "high"
        elif any(keyword in rec_lower for keyword in medium_keywords):
            return "medium"
        else:
            return "low"

    def _group_recommendations_by_category(
        self, recommendations: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group recommendations by analysis category."""
        grouped = {}

        for rec in recommendations:
            category = rec["category"]
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(rec)

        return grouped

    def _identify_security_strengths(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Identify security strengths from analysis results."""
        strengths = []

        # Check for good scores
        for analysis_name, analysis_result in analysis_results.items():
            if analysis_result.get("success"):
                score_key = {
                    "headers": "security_score",
                    "ssl_tls": "ssl_score",
                    "dns": "dns_security_score",
                }.get(analysis_name)

                if score_key and analysis_result.get(score_key, 0) >= 80:
                    strengths.append(f"Strong {analysis_name.replace('_', ' ')} configuration")

        # Check for specific security features
        dns_result = analysis_results.get("dns", {})
        if dns_result.get("success"):
            if dns_result.get("dnssec_status", {}).get("enabled"):
                strengths.append("DNSSEC enabled for DNS security")

            email_security = dns_result.get("email_security", {})
            if email_security.get("dmarc", {}).get("present"):
                strengths.append("DMARC policy implemented for email security")

        return strengths

    def _identify_security_weaknesses(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Identify security weaknesses from analysis results."""
        weaknesses = []

        # Check for poor scores
        for analysis_name, analysis_result in analysis_results.items():
            if analysis_result.get("success"):
                score_key = {
                    "headers": "security_score",
                    "ssl_tls": "ssl_score",
                    "dns": "dns_security_score",
                }.get(analysis_name)

                if score_key and analysis_result.get(score_key, 0) < 70:
                    weaknesses.append(f"Weak {analysis_name.replace('_', ' ')} configuration")

        # Check for specific security issues
        headers_result = analysis_results.get("headers", {})
        if headers_result.get("success"):
            missing_critical = [
                h for h in headers_result.get("missing_headers", []) if h.get("severity") == "high"
            ]
            if missing_critical:
                weaknesses.append("Missing critical HTTP security headers")

        dns_result = analysis_results.get("dns", {})
        if dns_result.get("success"):
            if not dns_result.get("dnssec_status", {}).get("enabled"):
                weaknesses.append("DNSSEC not enabled - vulnerable to DNS attacks")

        return weaknesses

    def _assess_compliance_readiness(self, analysis_results: Dict[str, Any]) -> str:
        """Assess readiness for security compliance frameworks."""
        total_score = 0
        count = 0

        for analysis_name, analysis_result in analysis_results.items():
            if analysis_result.get("success"):
                score_key = {
                    "headers": "security_score",
                    "ssl_tls": "ssl_score",
                    "dns": "dns_security_score",
                }.get(analysis_name)

                if score_key and score_key in analysis_result:
                    total_score += analysis_result[score_key]
                    count += 1

        avg_score = total_score / count if count > 0 else 0

        if avg_score >= 85:
            return "High compliance readiness"
        elif avg_score >= 70:
            return "Moderate compliance readiness"
        else:
            return "Low compliance readiness - significant improvements needed"

    def _calculate_grade_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Calculate distribution of grades."""
        distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}

        for score in scores:
            grade = self._score_to_grade(score)
            distribution[grade] += 1

        return distribution

    def _identify_common_issues(self, scan_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify common security issues across multiple scans."""
        issue_counts = {}

        for result in scan_results:
            analysis_results = result.get("analysis_results", {})

            # Count missing headers
            headers_result = analysis_results.get("headers", {})
            if headers_result.get("success"):
                for header in headers_result.get("missing_headers", []):
                    issue_key = f"Missing {header.get('name', 'Unknown Header')}"
                    issue_counts[issue_key] = issue_counts.get(issue_key, 0) + 1

            # Count DNS issues
            dns_result = analysis_results.get("dns", {})
            if dns_result.get("success"):
                if not dns_result.get("dnssec_status", {}).get("enabled"):
                    issue_counts["DNSSEC not enabled"] = (
                        issue_counts.get("DNSSEC not enabled", 0) + 1
                    )

                email_security = dns_result.get("email_security", {})
                if not email_security.get("dmarc", {}).get("present"):
                    issue_counts["DMARC not implemented"] = (
                        issue_counts.get("DMARC not implemented", 0) + 1
                    )

        # Convert to list and sort by frequency
        common_issues = [
            {
                "issue": issue,
                "affected_targets": count,
                "percentage": round(count / len(scan_results) * 100, 1),
            }
            for issue, count in issue_counts.items()
            if count > 1  # Only issues affecting multiple targets
        ]

        return sorted(common_issues, key=lambda x: x["affected_targets"], reverse=True)[:10]

    def _calculate_best_practices_adoption(
        self, scan_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate adoption of security best practices."""
        practices = {
            "hsts_enabled": 0,
            "csp_implemented": 0,
            "dnssec_enabled": 0,
            "dmarc_implemented": 0,
            "strong_ssl": 0,
        }

        for result in scan_results:
            analysis_results = result.get("analysis_results", {})

            # Check headers
            headers_result = analysis_results.get("headers", {})
            if headers_result.get("success"):
                headers_analysis = headers_result.get("headers_analysis", {})
                if "strict-transport-security" in headers_analysis and headers_analysis[
                    "strict-transport-security"
                ].get("present"):
                    practices["hsts_enabled"] += 1
                if "content-security-policy" in headers_analysis and headers_analysis[
                    "content-security-policy"
                ].get("present"):
                    practices["csp_implemented"] += 1

            # Check DNS
            dns_result = analysis_results.get("dns", {})
            if dns_result.get("success"):
                if dns_result.get("dnssec_status", {}).get("enabled"):
                    practices["dnssec_enabled"] += 1

                email_security = dns_result.get("email_security", {})
                if email_security.get("dmarc", {}).get("present"):
                    practices["dmarc_implemented"] += 1

            # Check SSL
            ssl_result = analysis_results.get("ssl_tls", {})
            if ssl_result.get("success") and ssl_result.get("ssl_score", 0) >= 80:
                practices["strong_ssl"] += 1

        total_targets = len(scan_results)

        return {
            practice: {
                "adopted_by": count,
                "total_targets": total_targets,
                "adoption_rate": round(count / total_targets * 100, 1),
            }
            for practice, count in practices.items()
        }

    def _identify_improvement_opportunities(self, scan_results: List[Dict[str, Any]]) -> List[str]:
        """Identify improvement opportunities across all targets."""
        opportunities = []

        # Calculate average scores
        avg_scores = {}
        score_mapping = {
            "headers": "security_score",
            "ssl_tls": "ssl_score",
            "dns": "dns_security_score",
        }

        for analysis_name, score_key in score_mapping.items():
            scores = []
            for result in scan_results:
                analysis_result = result.get("analysis_results", {}).get(analysis_name, {})
                if analysis_result.get("success") and score_key in analysis_result:
                    scores.append(analysis_result[score_key])

            if scores:
                avg_scores[analysis_name] = sum(scores) / len(scores)

        # Identify improvement opportunities
        for analysis_name, avg_score in avg_scores.items():
            if avg_score < 80:
                opportunities.append(
                    f"Improve {analysis_name.replace('_', ' ')} configuration across all targets"
                )

        # Check for common missing features
        common_issues = self._identify_common_issues(scan_results)
        for issue in common_issues[:3]:  # Top 3 issues
            if issue["percentage"] > 50:  # Affecting more than half of targets
                opportunities.append(f"Address widespread issue: {issue['issue']}")

        return opportunities

    def _detect_specific_changes(
        self, baseline: Dict[str, Any], current: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect specific changes between baseline and current scan."""
        changes = []

        # Compare analysis scores
        score_mapping = {
            "headers": "security_score",
            "ssl_tls": "ssl_score",
            "dns": "dns_security_score",
        }

        for analysis_name, score_key in score_mapping.items():
            baseline_analysis = baseline.get("analysis_results", {}).get(analysis_name, {})
            current_analysis = current.get("analysis_results", {}).get(analysis_name, {})

            if (
                baseline_analysis.get("success")
                and current_analysis.get("success")
                and score_key in baseline_analysis
                and score_key in current_analysis
            ):

                baseline_score = baseline_analysis[score_key]
                current_score = current_analysis[score_key]
                score_change = current_score - baseline_score

                if abs(score_change) >= 5:  # Significant change
                    changes.append(
                        {
                            "category": analysis_name.replace("_", " ").title(),
                            "change_type": "score_change",
                            "baseline_value": baseline_score,
                            "current_value": current_score,
                            "change": score_change,
                            "direction": "improved" if score_change > 0 else "degraded",
                        }
                    )

        return changes

    def _generate_change_summary(
        self, score_change: float, specific_changes: List[Dict[str, Any]]
    ) -> str:
        """Generate human-readable change summary."""
        if abs(score_change) < 1:
            return "No significant security changes detected"
        elif score_change > 0:
            return f"Security posture improved by {score_change} points"
        else:
            return f"Security posture degraded by {abs(score_change)} points"

    # Public utility methods
    def get_scan_profiles(self) -> Dict[str, Any]:
        """Get available scan profiles and their descriptions."""
        return {
            profile: {
                "description": config["description"],
                "analyses_included": [
                    analysis
                    for analysis, enabled in config.items()
                    if analysis.startswith("include_") and enabled
                ],
            }
            for profile, config in self.scan_profiles.items()
        }

    def validate_target_accessibility(self, target: str) -> Dict[str, Any]:
        """Validate that a target is accessible for scanning."""
        try:
            normalized = self._normalize_target(target)
            if not normalized["success"]:
                return normalized

            # This would include basic connectivity checks
            # For now, just return the normalization result
            return {
                "success": True,
                "accessible": True,
                "normalized_target": normalized,
                "validation_timestamp": time.time(),
            }

        except Exception as e:
            return {"success": False, "accessible": False, "error": str(e)}
