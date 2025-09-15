"""
Quick Scan Implementation

Provides immediate vulnerability scanning without dependency installation to prevent SSE timeouts.
"""

import asyncio
import json
import os
import tempfile
import time
from typing import Dict, Any, Optional

from shared.utils.logging import logger


class QuickSnykScanner:
    """Fast Snyk scanner that avoids dependency installation to prevent timeouts."""
    
    def __init__(self):
        self.timeout = 60  # Maximum 60 seconds total
    
    async def quick_github_scan(self, repo_url: str, progress_callback=None) -> Dict[str, Any]:
        """
        Perform a fast GitHub repository scan without dependency installation.
        
        Args:
            repo_url: GitHub repository URL
            progress_callback: Function for progress updates
            
        Returns:
            Dictionary with scan results
        """
        start_time = time.time()
        clone_dir = None
        
        try:
            if progress_callback:
                progress_callback("🚀 Starting quick vulnerability scan", "start")
            
            # Create temporary directory
            clone_dir = tempfile.mkdtemp(prefix="quick_snyk_")
            
            if progress_callback:
                progress_callback("📥 Cloning repository (shallow clone)...", "clone")
            
            # Quick shallow clone
            clone_cmd = ["git", "clone", "--depth", "1", repo_url, clone_dir]
            clone_process = await asyncio.create_subprocess_exec(
                *clone_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(clone_process.communicate(), timeout=30)
                if clone_process.returncode != 0:
                    raise Exception(f"Clone failed: {stderr.decode()}")
            except asyncio.TimeoutError:
                clone_process.kill()
                raise Exception("Repository clone timed out")
            
            if progress_callback:
                progress_callback("✅ Repository cloned successfully", "clone_complete")
                progress_callback("🔍 Running quick Snyk scan (no dependencies)...", "scan")
            
            # Run Snyk without dependency installation
            scan_result = await self._quick_snyk_scan(clone_dir, progress_callback)
            
            elapsed = time.time() - start_time
            if progress_callback:
                progress_callback(f"✅ Quick scan completed in {elapsed:.1f}s", "complete")
            
            return {
                "success": True,
                "scan_type": "quick_scan",
                "repository_url": repo_url,
                "vulnerabilities_found": scan_result.get("vulnerability_count", 0),
                "critical_count": scan_result.get("critical", 0),
                "high_count": scan_result.get("high", 0),
                "medium_count": scan_result.get("medium", 0),
                "low_count": scan_result.get("low", 0),
                "scan_time_seconds": round(elapsed, 1),
                "note": "Quick scan without dependency installation - may miss some vulnerabilities",
                "recommendation": "For complete results, run full scan with dependency installation"
            }
            
        except Exception as e:
            error_msg = f"Quick scan failed: {str(e)}"
            logger.error(error_msg)
            
            if progress_callback:
                progress_callback(f"❌ {error_msg}", "error")
            
            return {
                "success": False,
                "error": error_msg,
                "scan_type": "quick_scan",
                "repository_url": repo_url,
                "scan_time_seconds": round(time.time() - start_time, 1)
            }
            
        finally:
            # Cleanup
            if clone_dir and os.path.exists(clone_dir):
                import shutil
                try:
                    shutil.rmtree(clone_dir)
                    if progress_callback:
                        progress_callback("🧹 Cleanup completed", "cleanup")
                except Exception as e:
                    logger.warning(f"Cleanup failed: {e}")
    
    async def _quick_snyk_scan(self, project_path: str, progress_callback=None) -> Dict[str, Any]:
        """
        Run a quick Snyk scan without dependency installation.
        
        Args:
            project_path: Path to the project
            progress_callback: Progress callback function
            
        Returns:
            Dictionary with scan results
        """
        try:
            # Try direct scan first (fastest)
            cmd = ["snyk", "test", "--json"]
            
            if progress_callback:
                progress_callback("🔍 Running direct Snyk scan...", "scan_direct")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
            except asyncio.TimeoutError:
                process.kill()
                if progress_callback:
                    progress_callback("⏰ Direct scan timed out, trying file-based scan...", "scan_timeout")
                return await self._try_file_based_scan(project_path, progress_callback)
            
            if stdout:
                try:
                    result = json.loads(stdout.decode())
                    if "vulnerabilities" in result:
                        return self._parse_vulnerabilities(result["vulnerabilities"])
                except json.JSONDecodeError:
                    pass
            
            # If direct scan failed, try file-based scan
            if progress_callback:
                progress_callback("🔄 Direct scan failed, trying file-based scan...", "scan_fallback")
            
            return await self._try_file_based_scan(project_path, progress_callback)
            
        except Exception as e:
            logger.error(f"Quick scan error: {e}")
            return {"vulnerability_count": 0, "error": str(e)}
    
    async def _try_file_based_scan(self, project_path: str, progress_callback=None) -> Dict[str, Any]:
        """Try scanning specific manifest files."""
        
        # Look for common manifest files
        manifest_files = ["package.json", "requirements.txt", "pom.xml", "Gemfile", "go.mod"]
        
        for manifest in manifest_files:
            manifest_path = os.path.join(project_path, manifest)
            if os.path.exists(manifest_path):
                if progress_callback:
                    progress_callback(f"📄 Found {manifest}, scanning...", "scan_file")
                
                try:
                    cmd = ["snyk", "test", "--json", f"--file={manifest}"]
                    
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        cwd=project_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=20)
                    
                    if stdout:
                        try:
                            result = json.loads(stdout.decode())
                            if "vulnerabilities" in result:
                                vuln_data = self._parse_vulnerabilities(result["vulnerabilities"])
                                if vuln_data["vulnerability_count"] > 0:
                                    return vuln_data
                        except json.JSONDecodeError:
                            continue
                            
                except Exception as e:
                    logger.debug(f"File-based scan failed for {manifest}: {e}")
                    continue
        
        # No vulnerabilities found or all scans failed
        return {"vulnerability_count": 0, "message": "No vulnerabilities detected or scan failed"}
    
    def _parse_vulnerabilities(self, vulnerabilities) -> Dict[str, Any]:
        """Parse vulnerability data into summary."""
        
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "unknown").lower()
            if severity in counts:
                counts[severity] += 1
        
        return {
            "vulnerability_count": len(vulnerabilities),
            "critical": counts["critical"],
            "high": counts["high"],
            "medium": counts["medium"],
            "low": counts["low"]
        }
