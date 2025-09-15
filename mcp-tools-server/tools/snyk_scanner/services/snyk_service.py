"""
Snyk Scanner Service

Core service implementation for Snyk CLI integration and vulnerability scanning.
"""

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import time
import signal
import weakref
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from shared.utils.logging import logger


@dataclass
class ProcessManager:
    """Manages running processes and cleanup."""
    
    active_processes: Set[asyncio.subprocess.Process] = field(default_factory=set)
    temp_directories: Set[str] = field(default_factory=set)
    
    def add_process(self, process: asyncio.subprocess.Process):
        """Add a process to track."""
        self.active_processes.add(process)
    
    def remove_process(self, process: asyncio.subprocess.Process):
        """Remove a process from tracking."""
        self.active_processes.discard(process)
    
    def add_temp_dir(self, temp_dir: str):
        """Add a temporary directory to track."""
        self.temp_directories.add(temp_dir)
    
    def remove_temp_dir(self, temp_dir: str):
        """Remove a temporary directory from tracking."""
        self.temp_directories.discard(temp_dir)
    
    async def cleanup_all(self):
        """Clean up all tracked processes and directories."""
        # Kill all active processes
        for process in list(self.active_processes):
            try:
                if process.returncode is None:  # Process is still running
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        process.kill()
                        await process.wait()
            except Exception as e:
                logger.warning(f"Failed to cleanup process: {e}")
            finally:
                self.remove_process(process)
        
        # Clean up all temporary directories
        for temp_dir in list(self.temp_directories):
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")
            finally:
                self.remove_temp_dir(temp_dir)


@dataclass
class SnykScanResult:
    """Data class for Snyk scan results."""
    
    success: bool
    project_path: str
    scan_type: str
    vulnerabilities: List[Dict[str, Any]]
    summary: Dict[str, int]
    error: Optional[str] = None
    execution_time: Optional[float] = None
    snyk_version: Optional[str] = None
    scan_timestamp: Optional[float] = None


@dataclass
class SnykConfig:
    """Configuration for Snyk scanning."""
    
    timeout: int = 300  # 5 minutes default timeout
    json_output: bool = True
    severity_threshold: str = "low"  # low, medium, high, critical
    include_dev_dependencies: bool = True
    fail_on_issues: bool = False
    trust_policies: bool = True
    org: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization configuration."""
        # Get org from environment if not set
        if not self.org:
            self.org = os.getenv("SNYK_ORG") or os.getenv("SNYK_CFG_ORG")


class SnykService:
    """Service class for Snyk CLI operations."""
    
    def __init__(self, config: Optional[SnykConfig] = None):
        """
        Initialize the SnykService.
        
        Args:
            config: Configuration for the Snyk service.
        """
        self.config = config or SnykConfig()
        self.process_manager = ProcessManager()
        self._scan_cache = {}
        self._cache_timeout = 300  # 5 minutes cache
        
        # Set up cleanup on exit
        import atexit
        atexit.register(lambda: asyncio.create_task(self.cleanup()) if hasattr(self, 'process_manager') else None)
    
    async def cleanup(self):
        """Clean up all resources."""
        try:
            await self.process_manager.cleanup_all()
            self._scan_cache.clear()
            logger.info("SnykService cleanup completed")
        except Exception as e:
            logger.error(f"Error during SnykService cleanup: {e}")
    
    def _get_cache_key(self, project_path: str, scan_type: str) -> str:
        """Generate cache key for scan results."""
        return f"{project_path}:{scan_type}:{int(time.time() // self._cache_timeout)}"
    
    def _get_cached_result(self, project_path: str, scan_type: str) -> Optional[SnykScanResult]:
        """Get cached scan result if available and not expired."""
        cache_key = self._get_cache_key(project_path, scan_type)
        return self._scan_cache.get(cache_key)
    
    def _cache_result(self, project_path: str, scan_type: str, result: SnykScanResult):
        """Cache scan result."""
        cache_key = self._get_cache_key(project_path, scan_type)
        self._scan_cache[cache_key] = result
        
        # Clean old cache entries
        current_time = time.time()
        expired_keys = [
            key for key, cached_result in self._scan_cache.items()
            if hasattr(cached_result, 'scan_timestamp') and 
            cached_result.scan_timestamp and 
            current_time - cached_result.scan_timestamp > self._cache_timeout
        ]
        for key in expired_keys:
            del self._scan_cache[key]
        logger.info("SnykService initialized")
    
    async def check_snyk_installation(self) -> Dict[str, Any]:
        """
        Check if Snyk CLI is installed and configured.
        
        Returns:
            Dict containing installation status and version info.
        """
        try:
            # Check Snyk version
            result = await self._run_snyk_command(["snyk", "--version"], timeout=10)
            
            if result["success"]:
                version = result["stdout"].strip()
                
                # Check authentication status
                auth_result = await self._run_snyk_command(["snyk", "auth", "--status"], timeout=10)
                auth_status = auth_result["success"]
                
                return {
                    "installed": True,
                    "version": version,
                    "authenticated": auth_status,
                    "auth_details": auth_result.get("stdout", "").strip() if auth_status else auth_result.get("stderr", ""),
                    "config_org": self.config.org
                }
            else:
                return {
                    "installed": False,
                    "error": result.get("stderr", "Snyk CLI not found"),
                    "authenticated": False
                }
                
        except Exception as e:
            logger.error(f"Error checking Snyk installation: {e}")
            return {
                "installed": False,
                "error": str(e),
                "authenticated": False
            }
    
    async def scan_project(
        self, 
        project_path: str, 
        scan_type: str = "test",
        additional_args: Optional[List[str]] = None
    ) -> SnykScanResult:
        """
        Scan a project for vulnerabilities using Snyk CLI with caching.
        
        Args:
            project_path: Path to the project directory to scan.
            scan_type: Type of scan ('test', 'monitor', 'code').
            additional_args: Additional arguments to pass to Snyk.
            
        Returns:
            SnykScanResult containing scan results.
        """
        start_time = time.time()
        
        try:
            # Check cache first for test scans
            if scan_type == "test":
                cached_result = self._get_cached_result(project_path, scan_type)
                if cached_result:
                    logger.info(f"Returning cached scan result for {project_path}")
                    return cached_result
            
            # Validate project path
            if not os.path.exists(project_path):
                return SnykScanResult(
                    success=False,
                    project_path=project_path,
                    scan_type=scan_type,
                    vulnerabilities=[],
                    summary={},
                    error=f"Project path does not exist: {project_path}",
                    scan_timestamp=time.time()
                )
            
            # Build Snyk command
            cmd = self._build_snyk_command(scan_type, additional_args)
            
            # Try multiple approaches for scanning
            scan_result = await self._try_multiple_scan_approaches(project_path, scan_type, cmd)
            
            execution_time = time.time() - start_time
            
            if scan_result:
                scan_result.execution_time = execution_time
                scan_result.scan_timestamp = time.time()
                
                # Cache successful test scans
                if scan_type == "test" and scan_result.success:
                    self._cache_result(project_path, scan_type, scan_result)
                
                return scan_result
            else:
                # All approaches failed
                result = SnykScanResult(
                    success=False,
                    project_path=project_path,
                    scan_type=scan_type,
                    vulnerabilities=[],
                    summary={},
                    execution_time=execution_time,
                    scan_timestamp=time.time(),
                    error="All scan approaches failed"
                )
                return result
                
        except Exception as e:
            logger.error(f"Error scanning project {project_path}: {e}")
            return SnykScanResult(
                success=False,
                project_path=project_path,
                scan_type=scan_type,
                vulnerabilities=[],
                summary={},
                error=str(e),
                execution_time=time.time() - start_time,
                scan_timestamp=time.time()
            )
    
    async def scan_github_repository(self, repo_url: str, temp_dir: Optional[str] = None) -> SnykScanResult:
        """
        Clone and scan a GitHub repository.
        
        Args:
            repo_url: GitHub repository URL.
            temp_dir: Optional temporary directory for cloning.
            
        Returns:
            SnykScanResult containing scan results.
        """
        start_time = time.time()
        clone_dir = None
        
        clone_dir = None
        try:
            # Create temporary directory if not provided
            if temp_dir:
                clone_dir = os.path.join(temp_dir, "snyk_scan_repo")
                os.makedirs(clone_dir, exist_ok=True)
            else:
                clone_dir = tempfile.mkdtemp(prefix="snyk_scan_")
            
            # Track the temporary directory
            self.process_manager.add_temp_dir(clone_dir)
            
            logger.info(f"Cloning repository {repo_url} to {clone_dir}")
            
            # Clone the repository
            clone_result = await self._run_git_command(
                ["clone", "--depth", "1", repo_url, clone_dir],
                timeout=120
            )
            
            if not clone_result["success"]:
                return SnykScanResult(
                    success=False,
                    project_path=repo_url,
                    scan_type="github_scan",
                    vulnerabilities=[],
                    summary={},
                    error=f"Failed to clone repository: {clone_result.get('stderr', 'Unknown error')}",
                    scan_timestamp=time.time()
                )
            
            # Install dependencies before scanning
            logger.info(f"Scanning repository directly for {repo_url}")
            
            # Install dependencies first to enable proper Snyk scanning
            logger.info("Installing dependencies to enable proper Snyk scanning...")
            
            # Debug: list the contents of the clone directory
            try:
                files = os.listdir(clone_dir)
                logger.debug(f"Files in clone directory: {files}")
                
                # Check if requirements.txt exists and show its contents
                req_file = os.path.join(clone_dir, "requirements.txt")
                if os.path.exists(req_file):
                    with open(req_file, 'r') as f:
                        req_content = f.read()
                    logger.debug(f"requirements.txt content: {req_content[:200]}...")
                    
                    # Install dependencies using virtual environment approach
                    logger.info("Installing Python dependencies...")
                    
                    # Try multiple installation approaches to ensure compatibility
                    install_success = False
                    
                    # Approach 1: Create a virtual environment in the project directory
                    venv_dir = os.path.join(clone_dir, ".venv")
                    
                    # Create virtual environment
                    venv_result = await self._run_command([
                        "python3", "-m", "venv", ".venv"
                    ], clone_dir)
                    
                    if venv_result.returncode == 0:
                        # Install dependencies in virtual environment
                        pip_path = os.path.join(venv_dir, "bin", "pip")
                        install_result = await self._run_command([
                            pip_path, "install", "-r", "requirements.txt"
                        ], clone_dir)
                        
                        if install_result.returncode == 0:
                            logger.info("Dependencies installed successfully in virtual environment")
                            install_success = True
                        else:
                            logger.warning(f"Virtual environment dependency installation failed: {install_result.stderr}")
                    
                    # Approach 2: Install as editable package if we have setup.py
                    if not install_success and os.path.exists(os.path.join(clone_dir, "setup.py")):
                        logger.info("Trying editable package installation...")
                        install_result = await self._run_command([
                            "pip3", "install", "-e", "."
                        ], clone_dir)
                        
                        if install_result.returncode == 0:
                            logger.info("Editable package installed successfully")
                            install_success = True
                    
                    # Approach 3: System-wide user installation
                    if not install_success:
                        logger.info("Trying user-level installation...")
                        install_result = await self._run_command([
                            "pip3", "install", "--user", "-r", "requirements.txt"
                        ], clone_dir)
                        
                        if install_result.returncode == 0:
                            logger.info("Dependencies installed successfully with user flag")
                            install_success = True
                        else:
                            logger.warning(f"User-level dependency installation failed: {install_result.stderr}")
                    
                    # Approach 4: Create setup.py and install as package
                    if not install_success:
                        logger.info("Creating setup.py and installing as package...")
                        if self._create_setup_py(clone_dir):
                            install_result = await self._run_command([
                                "pip3", "install", "-e", "."
                            ], clone_dir)
                            
                            if install_result.returncode == 0:
                                logger.info("Package installed successfully via setup.py")
                                install_success = True
                    
                    if not install_success:
                        logger.warning("All dependency installation approaches failed")
                else:
                    logger.debug("No requirements.txt found")
                    
                # Check for other manifest files and install dependencies accordingly
                if os.path.exists(os.path.join(clone_dir, "package.json")):
                    success = await self._setup_node_dependencies(clone_dir)
                    if success:
                        logger.info("Node.js dependencies setup completed successfully")
                    else:
                        logger.warning("Node.js dependencies setup failed, will attempt manifest-only scanning")
                        
            except Exception as e:
                logger.debug(f"Error during dependency installation: {e}")
            
            # Scan the cloned repository
            scan_result = await self.scan_project(clone_dir, "test")
            
            # Update the project path to show original repo URL
            scan_result.project_path = repo_url
            scan_result.scan_type = "github_scan"
            
            return scan_result
            
        except Exception as e:
            logger.error(f"Error scanning GitHub repository {repo_url}: {e}")
            return SnykScanResult(
                success=False,
                project_path=repo_url,
                scan_type="github_scan",
                vulnerabilities=[],
                summary={},
                error=str(e),
                execution_time=time.time() - start_time
            )
        finally:
            # Clean up temporary directory using process manager
            if clone_dir:
                self.process_manager.remove_temp_dir(clone_dir)
                if temp_dir is None:  # Only clean up if we created the temp dir
                    try:
                        shutil.rmtree(clone_dir, ignore_errors=True)
                        logger.debug(f"Cleaned up temporary directory: {clone_dir}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up temporary directory {clone_dir}: {e}")
    
    async def scan_code_analysis(self, project_path: str) -> SnykScanResult:
        """
        Perform static code analysis using Snyk Code.
        
        Args:
            project_path: Path to the project directory.
            
        Returns:
            SnykScanResult containing code analysis results.
        """
        return await self.scan_project(project_path, "code", ["--json"])
    
    async def get_snyk_version(self) -> Optional[str]:
        """
        Get the Snyk CLI version.
        
        Returns:
            Version string or None if not available.
        """
        try:
            result = await self._run_snyk_command(["snyk", "--version"], timeout=10)
            if result["success"]:
                return result["stdout"].strip()
            return None
        except Exception as e:
            logger.error(f"Error getting Snyk version: {e}")
            return None
    
    def _build_snyk_command(self, scan_type: str, additional_args: Optional[List[str]] = None) -> List[str]:
        """
        Build Snyk command with appropriate arguments.
        
        Args:
            scan_type: Type of scan to perform.
            additional_args: Additional arguments.
            
        Returns:
            List of command arguments.
        """
        cmd = ["snyk", scan_type]
        
        # Add common arguments
        if self.config.json_output and scan_type == "test":
            cmd.append("--json")
        
        # For different project types, let Snyk auto-detect
        if scan_type == "test":
            # Use simple auto-detection like the manual test that works
            pass  # Just use "snyk test --json" without additional flags
        
        if self.config.severity_threshold != "low":
            cmd.extend(["--severity-threshold", self.config.severity_threshold])
        
        if not self.config.include_dev_dependencies and scan_type == "test":
            cmd.append("--prod")
        
        if self.config.org:
            cmd.extend(["--org", self.config.org])
        
        # Add additional arguments if provided
        if additional_args:
            cmd.extend(additional_args)
        
        return cmd
    
    async def _run_snyk_command(
        self, 
        cmd: List[str], 
        cwd: Optional[str] = None, 
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Run a Snyk CLI command asynchronously with process tracking.
        
        Args:
            cmd: Command arguments.
            cwd: Working directory.
            timeout: Command timeout in seconds.
            
        Returns:
            Dict containing command result.
        """
        process = None
        try:
            logger.debug(f"Running Snyk command: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            # Track the process
            self.process_manager.add_process(process)
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Snyk command timed out after {timeout} seconds: {' '.join(cmd)}")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout} seconds",
                    "return_code": -1
                }
            finally:
                # Always remove from tracking
                if process:
                    self.process_manager.remove_process(process)
            
            return {
                "success": process.returncode in [0, 1, 2],  # 0=no vulns, 1=vulns found, 2=error but may have data
                "has_vulnerabilities": process.returncode == 1,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "return_code": process.returncode
            }
            
        except Exception as e:
            logger.error(f"Error running Snyk command: {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1
            }
    
    async def _run_command(
        self, 
        cmd: List[str], 
        cwd: Optional[str] = None, 
        timeout: int = 60
    ) -> subprocess.CompletedProcess:
        """
        Run a general command asynchronously with process tracking.
        
        Args:
            cmd: Command arguments.
            cwd: Working directory.
            timeout: Command timeout in seconds.
            
        Returns:
            CompletedProcess object with returncode, stdout, stderr.
        """
        process = None
        try:
            logger.debug(f"Running command: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            # Track the process
            self.process_manager.add_process(process)
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Command timed out after {timeout} seconds: {' '.join(cmd)}")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                
                # Create a mock CompletedProcess for timeout
                result = subprocess.CompletedProcess(
                    args=cmd,
                    returncode=-1,
                    stdout=b"",
                    stderr=f"Command timed out after {timeout} seconds".encode()
                )
                return result
            finally:
                # Always remove from tracking
                if process:
                    self.process_manager.remove_process(process)
            
            # Create CompletedProcess object
            result = subprocess.CompletedProcess(
                args=cmd,
                returncode=process.returncode,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace")
            )
            return result
            
        except Exception as e:
            logger.error(f"Error running command: {e}")
            if process:
                self.process_manager.remove_process(process)
            
            # Create error CompletedProcess
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=-1,
                stdout="",
                stderr=str(e)
            )

    async def _run_git_command(
        self, 
        cmd: List[str], 
        cwd: Optional[str] = None, 
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Run a Git command asynchronously.
        
        Args:
            cmd: Git command arguments.
            cwd: Working directory.
            timeout: Command timeout in seconds.
            
        Returns:
            Dict containing command result.
        """
        full_cmd = ["git"] + cmd
        
        # Use the general command runner for git commands
        result = await self._run_command(full_cmd, cwd, timeout)
        
        # Convert CompletedProcess to dict format for compatibility
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    
    async def _try_multiple_scan_approaches(self, project_path: str, scan_type: str, base_cmd: List[str]) -> Optional[SnykScanResult]:
        """
        Try multiple scanning approaches to handle different project configurations.
        
        Args:
            project_path: Path to the project to scan.
            scan_type: Type of scan ('test', 'monitor', etc.).
            base_cmd: Base Snyk command to try.
            
        Returns:
            SnykScanResult if any approach succeeds, None if all fail.
        """
        if scan_type != "test":
            # For non-test scans, just run the base command
            result = await self._run_snyk_command(base_cmd, cwd=project_path, timeout=self.config.timeout)
            if result.get("success"):
                return SnykScanResult(
                    success=True,
                    project_path=project_path,
                    scan_type=scan_type,
                    vulnerabilities=[],
                    summary={"monitoring_enabled": True} if scan_type == "monitor" else {},
                    scan_timestamp=time.time()
                )
            return None
        
        # For test scans, try multiple approaches based on detected languages
        approaches = await self._get_multi_language_approaches(project_path, base_cmd)
        
        for approach in approaches:
            if approach["scan_command"] is None:
                continue
                
            logger.info(f"Trying approach: {approach['name']}")
            
            # Run setup commands
            setup_success = True
            for setup_cmd in approach["setup_commands"]:
                if setup_cmd is None:
                    continue
                    
                setup_result = await self._run_command(setup_cmd, cwd=project_path)
                if setup_result.returncode != 0:
                    logger.warning(f"Setup command failed for {approach['name']}: {setup_result.stderr}")
                    setup_success = False
                    break
                else:
                    logger.info(f"Setup command succeeded for {approach['name']}")
            
            if not setup_success:
                continue
                
            # Prepare the scan command with environment prefix if needed
            scan_cmd = approach["scan_command"][:]
            if approach.get("env_prefix") and scan_cmd:
                # For virtual environment, we might need to use the venv's python
                # but Snyk should still be available globally
                pass  # Keep scan_cmd as is since Snyk is globally installed
                
            # Run Snyk scan
            if scan_cmd and scan_cmd[0] in ["bash", "env"]:
                # Use our general command runner for shell commands and env commands
                result_proc = await self._run_command(scan_cmd, cwd=project_path if scan_cmd[0] == "env" else None)
                result = {
                    "return_code": result_proc.returncode,
                    "stdout": result_proc.stdout,
                    "stderr": result_proc.stderr,
                    "success": result_proc.returncode in [0, 1]
                }
            else:
                result = await self._run_snyk_command(scan_cmd, cwd=project_path, timeout=self.config.timeout)
            
            # Debug logging
            logger.debug(f"Snyk command return code: {result.get('return_code')}")
            logger.debug(f"Snyk stdout length: {len(result.get('stdout', ''))}")
            logger.debug(f"Snyk stderr: {result.get('stderr', '')[:500]}")
            logger.debug(f"Working directory: {project_path}")
            logger.debug(f"Current user: {os.getenv('USER', 'unknown')}")
            logger.debug(f"Python path: {os.getenv('PYTHONPATH', 'not set')}")
            logger.debug(f"PATH: {os.getenv('PATH', 'not set')[:200]}...")
            if result.get("stdout"):
                logger.debug(f"Snyk stdout preview: {result['stdout'][:1000]}...")
            
            # Check if scan was successful
            if result.get("stdout"):
                try:
                    output_data = json.loads(result["stdout"])
                    # Return code 0 = no vulnerabilities, 1 = vulnerabilities found, both are success
                    # For return code 1 (vulnerabilities found), we should proceed even if "ok" is false
                    if result.get("return_code") == 0 or (result.get("return_code") == 1 and "vulnerabilities" in output_data):
                        vulnerabilities, summary = self._parse_scan_output(result["stdout"])
                        logger.info(f"Successful scan with approach: {approach['name']}, found {len(vulnerabilities)} vulnerabilities")
                        return SnykScanResult(
                            success=True,
                            project_path=project_path,
                            scan_type=scan_type,
                            vulnerabilities=vulnerabilities,
                            summary=summary,
                            scan_timestamp=time.time()
                        )
                    else:
                        error_msg = output_data.get('error', 'Unknown error')
                        language = approach.get('language', 'unknown')
                        
                        # Provide language-specific error guidance
                        guidance = self._get_language_specific_error_guidance(language, error_msg)
                        logger.warning(f"Approach {approach['name']} failed: {error_msg}")
                        if guidance:
                            logger.info(f"Suggestion for {language}: {guidance}")
                            
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON output for {approach['name']}: {e}")
                    continue
            else:
                logger.warning(f"Approach {approach['name']} produced no output")
        
        # All approaches failed
        logger.warning("All scanning approaches failed")
        return None
    
    def _get_direct_file_scan_command(self, project_path: str) -> Optional[List[str]]:
        """Get command for direct file scanning based on what manifest files exist."""
        manifest_files = [
            ("requirements.txt", "pip"),
            ("package.json", "npm"),
            ("pom.xml", "maven"),
            ("Gemfile", "rubygems")
        ]
        
        for manifest_file, _ in manifest_files:
            if os.path.exists(os.path.join(project_path, manifest_file)):
                return ["snyk", "test", "--json", f"--file={manifest_file}"]
        
        return None
    
    def _get_venv_scan_command(self, project_path: str) -> Optional[List[str]]:
        """Get virtual environment scan command if .venv exists."""
        venv_dir = os.path.join(project_path, ".venv")
        if os.path.exists(venv_dir):
            # Check for both Unix and Windows-style venv structures
            venv_python_unix = os.path.join(venv_dir, "bin", "python")
            venv_python_win = os.path.join(venv_dir, "Scripts", "python.exe")
            
            if os.path.exists(venv_python_unix):
                return ["bash", "-c", f"cd \"{project_path}\" && source .venv/bin/activate && snyk test --json"]
            elif os.path.exists(venv_python_win):
                return ["cmd", "/c", f"cd \"{project_path}\" && .venv\\Scripts\\activate && snyk test --json"]
        
        return None

    def _create_setup_py(self, project_path: str) -> bool:
        """Create a minimal setup.py file to help Snyk recognize the project."""
        try:
            if not os.path.exists(os.path.join(project_path, "requirements.txt")):
                return False
                
            setup_py_content = '''
from setuptools import setup

# Read requirements
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='temp-project',
    version='0.1.0',
    install_requires=requirements,
    packages=[],
)
'''
            setup_py_path = os.path.join(project_path, "setup.py")
            if not os.path.exists(setup_py_path):
                with open(setup_py_path, 'w') as f:
                    f.write(setup_py_content)
                logger.debug("Created setup.py for Snyk scanning")
            return True
        except Exception as e:
            logger.debug(f"Failed to create setup.py: {e}")
            return False

    def _check_snyk_python_module(self) -> bool:
        """Check if Snyk is available as a Python module."""
        try:
            import subprocess
            result = subprocess.run(["python3", "-m", "snyk", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

    async def _get_multi_language_approaches(self, project_path: str, base_cmd: List[str]) -> List[dict]:
        """
        Get scanning approaches tailored to the detected languages in the project.
        
        Args:
            project_path: Path to the project to scan.
            base_cmd: Base Snyk command.
            
        Returns:
            List of scanning approaches ordered by likelihood of success.
        """
        detected_languages = self._detect_project_languages(project_path)
        approaches = []
        
        # Node.js/JavaScript approaches
        if "javascript" in detected_languages or "typescript" in detected_languages:
            approaches.extend([
                {
                    "name": "Node.js package.json direct scan",
                    "setup_commands": [],
                    "scan_command": ["snyk", "test", "--json", "--file=package.json"],
                    "env_prefix": None,
                    "language": "javascript"
                },
                {
                    "name": "Node.js with package-lock.json scan",
                    "setup_commands": [],
                    "scan_command": ["snyk", "test", "--json", "--file=package-lock.json"] if os.path.exists(os.path.join(project_path, "package-lock.json")) else None,
                    "env_prefix": None,
                    "language": "javascript"
                },
                {
                    "name": "Node.js yarn.lock scan",
                    "setup_commands": [],
                    "scan_command": ["snyk", "test", "--json", "--file=yarn.lock"] if os.path.exists(os.path.join(project_path, "yarn.lock")) else None,
                    "env_prefix": None,
                    "language": "javascript"
                },
                {
                    "name": "Node.js with dependencies (safe install)",
                    "setup_commands": [
                        ["npm", "install", "--production", "--ignore-scripts", "--no-audit"]
                    ],
                    "scan_command": ["snyk", "test", "--json"],
                    "env_prefix": None,
                    "language": "javascript"
                },
                {
                    "name": "Node.js CI install scan",
                    "setup_commands": [
                        ["npm", "ci", "--production", "--ignore-scripts"] if os.path.exists(os.path.join(project_path, "package-lock.json")) else None
                    ],
                    "scan_command": ["snyk", "test", "--json"],
                    "env_prefix": None,
                    "language": "javascript"
                }
            ])
        
        # Python approaches
        if "python" in detected_languages:
            approaches.extend([
                {
                    "name": "Python requirements.txt direct scan",
                    "setup_commands": [],
                    "scan_command": ["snyk", "test", "--json", "--file=requirements.txt"] if os.path.exists(os.path.join(project_path, "requirements.txt")) else None,
                    "env_prefix": None,
                    "language": "python"
                },
                {
                    "name": "Python Pipfile scan",
                    "setup_commands": [],
                    "scan_command": ["snyk", "test", "--json", "--file=Pipfile"] if os.path.exists(os.path.join(project_path, "Pipfile")) else None,
                    "env_prefix": None,
                    "language": "python"
                },
                {
                    "name": "Python pyproject.toml scan",
                    "setup_commands": [],
                    "scan_command": ["snyk", "test", "--json", "--file=pyproject.toml"] if os.path.exists(os.path.join(project_path, "pyproject.toml")) else None,
                    "env_prefix": None,
                    "language": "python"
                },
                {
                    "name": "Python pip environment setup scan",
                    "setup_commands": [
                        ["pip3", "install", "--upgrade", "pip"],
                        ["pip3", "install", "-e", "."] if os.path.exists(os.path.join(project_path, "setup.py")) else None
                    ],
                    "scan_command": ["snyk", "test", "--json"],
                    "env_prefix": None,
                    "language": "python"
                },
                {
                    "name": "Python virtual environment scan",
                    "setup_commands": [],
                    "scan_command": self._get_venv_scan_command(project_path),
                    "env_prefix": None,
                    "language": "python"
                }
            ])
        
        # Java approaches
        if "java" in detected_languages:
            approaches.extend([
                {
                    "name": "Java Maven pom.xml scan",
                    "setup_commands": [],
                    "scan_command": ["snyk", "test", "--json", "--file=pom.xml"] if os.path.exists(os.path.join(project_path, "pom.xml")) else None,
                    "env_prefix": None,
                    "language": "java"
                },
                {
                    "name": "Java Gradle build.gradle scan",
                    "setup_commands": [],
                    "scan_command": ["snyk", "test", "--json", "--file=build.gradle"] if os.path.exists(os.path.join(project_path, "build.gradle")) else None,
                    "env_prefix": None,
                    "language": "java"
                },
                {
                    "name": "Java with Maven dependencies",
                    "setup_commands": [
                        ["mvn", "dependency:resolve"] if os.path.exists(os.path.join(project_path, "pom.xml")) else None
                    ],
                    "scan_command": ["snyk", "test", "--json"],
                    "env_prefix": None,
                    "language": "java"
                }
            ])
        
        # Ruby approaches
        if "ruby" in detected_languages:
            approaches.extend([
                {
                    "name": "Ruby Gemfile direct scan",
                    "setup_commands": [],
                    "scan_command": ["snyk", "test", "--json", "--file=Gemfile"] if os.path.exists(os.path.join(project_path, "Gemfile")) else None,
                    "env_prefix": None,
                    "language": "ruby"
                },
                {
                    "name": "Ruby Gemfile.lock scan",
                    "setup_commands": [],
                    "scan_command": ["snyk", "test", "--json", "--file=Gemfile.lock"] if os.path.exists(os.path.join(project_path, "Gemfile.lock")) else None,
                    "env_prefix": None,
                    "language": "ruby"
                },
                {
                    "name": "Ruby with bundle install",
                    "setup_commands": [
                        ["bundle", "install", "--deployment"] if os.path.exists(os.path.join(project_path, "Gemfile.lock")) else ["bundle", "install"]
                    ],
                    "scan_command": ["snyk", "test", "--json"],
                    "env_prefix": None,
                    "language": "ruby"
                }
            ])
        
        # Go approaches
        if "go" in detected_languages:
            approaches.extend([
                {
                    "name": "Go go.mod direct scan",
                    "setup_commands": [],
                    "scan_command": ["snyk", "test", "--json", "--file=go.mod"] if os.path.exists(os.path.join(project_path, "go.mod")) else None,
                    "env_prefix": None,
                    "language": "go"
                },
                {
                    "name": "Go vendor scan",
                    "setup_commands": [
                        ["go", "mod", "vendor"] if os.path.exists(os.path.join(project_path, "go.mod")) else None
                    ],
                    "scan_command": ["snyk", "test", "--json"],
                    "env_prefix": None,
                    "language": "go"
                }
            ])
        
        # .NET approaches
        if "csharp" in detected_languages or "dotnet" in detected_languages:
            approaches.extend([
                {
                    "name": ".NET packages.config scan",
                    "setup_commands": [],
                    "scan_command": ["snyk", "test", "--json", "--file=packages.config"] if os.path.exists(os.path.join(project_path, "packages.config")) else None,
                    "env_prefix": None,
                    "language": "dotnet"
                },
                {
                    "name": ".NET project.json scan",
                    "setup_commands": [],
                    "scan_command": ["snyk", "test", "--json", "--file=project.json"] if os.path.exists(os.path.join(project_path, "project.json")) else None,
                    "env_prefix": None,
                    "language": "dotnet"
                }
            ])
        
        # PHP approaches
        if "php" in detected_languages:
            approaches.extend([
                {
                    "name": "PHP composer.json direct scan",
                    "setup_commands": [],
                    "scan_command": ["snyk", "test", "--json", "--file=composer.json"] if os.path.exists(os.path.join(project_path, "composer.json")) else None,
                    "env_prefix": None,
                    "language": "php"
                },
                {
                    "name": "PHP composer.lock scan",
                    "setup_commands": [],
                    "scan_command": ["snyk", "test", "--json", "--file=composer.lock"] if os.path.exists(os.path.join(project_path, "composer.lock")) else None,
                    "env_prefix": None,
                    "language": "php"
                }
            ])
        
        # Generic fallback approaches
        approaches.extend([
            {
                "name": "All projects auto-detect scan",
                "setup_commands": [],
                "scan_command": ["snyk", "test", "--json", "--all-projects"],
                "env_prefix": None,
                "language": "generic"
            },
            {
                "name": "Direct scan with project files",
                "setup_commands": [],
                "scan_command": base_cmd,
                "env_prefix": None,
                "language": "generic"
            },
            {
                "name": "Shell script scan (mimics manual)",
                "setup_commands": [],
                "scan_command": ["bash", "-c", f"cd \"{project_path}\" && snyk test --json"],
                "env_prefix": None,
                "language": "generic"
            }
        ])
        
        # Filter out None commands and return
        return [approach for approach in approaches if approach["scan_command"] is not None]

    def _detect_project_languages(self, project_path: str) -> Set[str]:
        """
        Detect programming languages used in the project based on manifest files and file extensions.
        
        Args:
            project_path: Path to the project directory.
            
        Returns:
            Set of detected language identifiers.
        """
        languages = set()
        
        # Check for manifest files
        manifest_indicators = {
            "package.json": {"javascript", "typescript"},
            "package-lock.json": {"javascript"},
            "yarn.lock": {"javascript", "typescript"},
            "requirements.txt": {"python"},
            "setup.py": {"python"},
            "pyproject.toml": {"python"},
            "Pipfile": {"python"},
            "pom.xml": {"java"},
            "build.gradle": {"java"},
            "build.gradle.kts": {"java"},
            "Gemfile": {"ruby"},
            "go.mod": {"go"},
            "composer.json": {"php"},
            "packages.config": {"csharp", "dotnet"},
            "project.json": {"csharp", "dotnet"},
            "*.csproj": {"csharp", "dotnet"},
            "*.sln": {"csharp", "dotnet"}
        }
        
        try:
            # Check manifest files
            for file_pattern, lang_set in manifest_indicators.items():
                if "*" in file_pattern:
                    # Handle glob patterns
                    import glob
                    matches = glob.glob(os.path.join(project_path, file_pattern))
                    if matches:
                        languages.update(lang_set)
                else:
                    if os.path.exists(os.path.join(project_path, file_pattern)):
                        languages.update(lang_set)
            
            # Check common file extensions for additional detection
            file_extensions = {
                ".py": "python",
                ".js": "javascript", 
                ".ts": "typescript",
                ".jsx": "javascript",
                ".tsx": "typescript",
                ".java": "java",
                ".rb": "ruby",
                ".go": "go",
                ".php": "php",
                ".cs": "csharp",
                ".vb": "dotnet"
            }
            
            # Sample a few files to detect languages
            for root, dirs, files in os.walk(project_path):
                # Skip node_modules, .git, and other common ignore directories
                dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '.venv', '__pycache__', 'target', 'build'}]
                
                for file in files[:20]:  # Limit to first 20 files for performance
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext in file_extensions:
                        languages.add(file_extensions[file_ext])
                
                # Don't recurse too deep
                if len(root.split(os.sep)) - len(project_path.split(os.sep)) > 2:
                    break
                    
        except Exception as e:
            logger.debug(f"Error detecting project languages: {e}")
        
        logger.info(f"Detected languages in {project_path}: {', '.join(languages) if languages else 'none'}")
        return languages

    def _get_language_specific_error_guidance(self, language: str, error_msg: str) -> Optional[str]:
        """
        Provide language-specific guidance for common Snyk scanning errors.
        
        Args:
            language: The programming language being scanned.
            error_msg: The error message from Snyk.
            
        Returns:
            Helpful guidance string or None.
        """
        error_lower = error_msg.lower()
        
        if language == "javascript" or language == "typescript":
            if "missing node_modules" in error_lower or "npm install" in error_lower:
                return "Node.js dependencies missing. Try running 'npm install' or use manifest-only scanning with --file=package.json"
            elif "lock file" in error_lower:
                return "Lock file issues detected. Try deleting node_modules and package-lock.json, then run 'npm install'"
            elif "native dependencies" in error_lower or "gyp" in error_lower:
                return "Native dependency compilation failed. Try 'npm install --ignore-scripts' or use manifest-only scanning"
                
        elif language == "python":
            if "requirements.txt" in error_lower:
                return "Python requirements file issues. Ensure requirements.txt exists and is properly formatted"
            elif "pip" in error_lower and "install" in error_lower:
                return "Python package installation failed. Try using a virtual environment or manifest-only scanning"
                
        elif language == "java":
            if "pom.xml" in error_lower or "maven" in error_lower:
                return "Maven project issues. Ensure pom.xml is valid and dependencies can be resolved"
            elif "gradle" in error_lower:
                return "Gradle project issues. Ensure build.gradle is valid and dependencies can be resolved"
                
        elif language == "ruby":
            if "gemfile" in error_lower or "bundle" in error_lower:
                return "Ruby gem issues. Try running 'bundle install' or use manifest-only scanning with --file=Gemfile"
                
        elif language == "go":
            if "go.mod" in error_lower:
                return "Go module issues. Ensure go.mod is valid and try 'go mod tidy'"
                
        elif language == "php":
            if "composer" in error_lower:
                return "Composer issues. Ensure composer.json is valid and try 'composer install'"
        
        return None

    async def _fallback_scan(self, project_path: str, scan_type: str, execution_time: float) -> SnykScanResult:
        """
        Fallback scan approach when the main scan fails.
        
        Args:
            project_path: Path to the project to scan.
            scan_type: Type of scan.
            execution_time: Time already spent on scanning.
            
        Returns:
            SnykScanResult with fallback scan results.
        """
        try:
            logger.info("Attempting fallback scan with direct file scanning...")
            
            # Try scanning specific manifest files directly
            manifest_files = [
                ("requirements.txt", "pip"),
                ("package.json", "npm"),
                ("pom.xml", "maven"),
                ("Gemfile", "rubygems")
            ]
            
            for manifest_file, package_manager in manifest_files:
                manifest_path = os.path.join(project_path, manifest_file)
                if os.path.exists(manifest_path):
                    logger.info(f"Trying direct scan of {manifest_file}...")
                    
                    # Build command for direct file scanning
                    cmd = ["snyk", "test", "--json", f"--file={manifest_file}"]
                    
                    # Run the direct file scan
                    result = await self._run_snyk_command(cmd, cwd=project_path, timeout=120)
                    
                    if result.get("stdout") and result["return_code"] in [0, 1]:
                        # Try to parse the result
                        try:
                            output_data = json.loads(result["stdout"])
                            if output_data.get("ok") is not False:
                                vulnerabilities, summary = self._parse_scan_output(result["stdout"])
                                logger.info(f"Fallback scan successful with {len(vulnerabilities)} vulnerabilities found")
                                return SnykScanResult(
                                    success=True,
                                    project_path=project_path,
                                    scan_type=f"{scan_type}_fallback",
                                    vulnerabilities=vulnerabilities,
                                    summary=summary,
                                    execution_time=execution_time,
                                    scan_timestamp=time.time()
                                )
                        except json.JSONDecodeError:
                            continue
            
            # If all fallback attempts fail, return empty result
            logger.warning("All fallback scan attempts failed")
            return SnykScanResult(
                success=False,
                project_path=project_path,
                scan_type=scan_type,
                vulnerabilities=[],
                summary={},
                execution_time=execution_time,
                scan_timestamp=time.time(),
                error="All scan attempts failed"
            )
            
        except Exception as e:
            logger.error(f"Error in fallback scan: {e}")
            return SnykScanResult(
                success=False,
                project_path=project_path,
                scan_type=scan_type,
                vulnerabilities=[],
                summary={},
                execution_time=execution_time,
                scan_timestamp=time.time(),
                error=str(e)
            )

    async def _setup_python_environment(self, project_path: str) -> bool:
        """
        Set up a minimal environment for Snyk to work with different project types.
        
        Args:
            project_path: Path to the project directory.
            
        Returns:
            True if setup was successful, False otherwise.
        """
        try:
            logger.info("Setting up environment for Snyk scanning...")
            
            # Check for different manifest files and set up accordingly
            project_files = {
                "requirements.txt": self._setup_python_project,
                "package.json": self._setup_node_project,
                "pom.xml": self._setup_java_project,
                "Gemfile": self._setup_ruby_project,
            }
            
            setup_success = False
            for file_name, setup_func in project_files.items():
                file_path = os.path.join(project_path, file_name)
                if os.path.exists(file_path):
                    logger.info(f"Found {file_name}, setting up {file_name.split('.')[0]} environment...")
                    if await setup_func(project_path):
                        setup_success = True
                    break  # Use the first manifest file found
            
            return setup_success
            
        except Exception as e:
            logger.warning(f"Error setting up environment: {e}")
            return False

    async def _setup_python_project(self, project_path: str) -> bool:
        """Setup Python project for Snyk scanning."""
        try:
            # Instead of creating setup.py, let's try to install a minimal package
            # to create a proper Python environment
            logger.info("Creating minimal Python environment...")
            
            # Create a minimal requirements file for Snyk to work with
            minimal_req_path = os.path.join(project_path, "snyk_minimal.txt")
            with open(minimal_req_path, "w") as f:
                f.write("setuptools>=40.0\n")
            
            # Try to install this minimal requirement
            install_result = await self._run_dependency_command(
                ["pip", "install", "--user", "-r", "snyk_minimal.txt"],
                project_path
            )
            
            if install_result["success"]:
                logger.info("Successfully set up minimal Python environment")
            else:
                logger.warning(f"Failed to set up minimal environment: {install_result.get('stderr', '')}")
            
            return True
        except Exception as e:
            logger.warning(f"Error setting up Python project: {e}")
            return False

    async def _setup_node_project(self, project_path: str) -> bool:
        """Setup Node.js project for Snyk scanning."""
        try:
            # For Node.js projects, we mainly need to ensure package.json is valid
            # Snyk should be able to scan package.json directly
            return True
        except Exception as e:
            logger.warning(f"Error setting up Node.js project: {e}")
            return False

    async def _setup_node_dependencies(self, project_path: str) -> bool:
        """
        Enhanced Node.js dependency setup with multiple fallback strategies.
        
        Args:
            project_path: Path to the Node.js project.
            
        Returns:
            True if any dependency setup strategy succeeded, False otherwise.
        """
        try:
            logger.info("Setting up Node.js dependencies with multiple strategies...")
            
            # Strategy 1: Try npm ci first (if package-lock.json exists)
            if os.path.exists(os.path.join(project_path, "package-lock.json")):
                logger.info("Attempting npm ci (clean install)...")
                result = await self._run_command(["npm", "ci", "--production", "--ignore-scripts"], project_path)
                if result.returncode == 0:
                    logger.info("npm ci completed successfully")
                    return True
                else:
                    logger.warning(f"npm ci failed: {result.stderr[:500]}")
            
            # Strategy 2: Try safe npm install
            logger.info("Attempting safe npm install...")
            result = await self._run_command(["npm", "install", "--production", "--ignore-scripts", "--no-audit"], project_path)
            if result.returncode == 0:
                logger.info("Safe npm install completed successfully")
                return True
            else:
                logger.warning(f"Safe npm install failed: {result.stderr[:500]}")
            
            # Strategy 3: Try npm install with --no-optional to skip optional dependencies
            logger.info("Attempting npm install without optional dependencies...")
            result = await self._run_command(["npm", "install", "--no-optional", "--ignore-scripts"], project_path)
            if result.returncode == 0:
                logger.info("npm install without optional dependencies completed successfully")
                return True
            else:
                logger.warning(f"npm install without optional dependencies failed: {result.stderr[:500]}")
            
            # Strategy 4: Try yarn if available and yarn.lock exists
            if os.path.exists(os.path.join(project_path, "yarn.lock")):
                logger.info("Attempting yarn install...")
                result = await self._run_command(["yarn", "install", "--production", "--ignore-scripts"], project_path)
                if result.returncode == 0:
                    logger.info("yarn install completed successfully")
                    return True
                else:
                    logger.warning(f"yarn install failed: {result.stderr[:500]}")
            
            # If all strategies fail, we'll still attempt scanning with manifest files only
            logger.warning("All Node.js dependency installation strategies failed, will scan manifest files directly")
            return False
            
        except Exception as e:
            logger.warning(f"Error during Node.js dependency setup: {e}")
            return False

    async def _setup_java_project(self, project_path: str) -> bool:
        """Setup Java project for Snyk scanning."""
        try:
            # For Java projects with pom.xml, Snyk should work directly
            return True
        except Exception as e:
            logger.warning(f"Error setting up Java project: {e}")
            return False

    async def _setup_ruby_project(self, project_path: str) -> bool:
        """Setup Ruby project for Snyk scanning."""
        try:
            # For Ruby projects with Gemfile, Snyk should work directly
            return True
        except Exception as e:
            logger.warning(f"Error setting up Ruby project: {e}")
            return False

    async def _install_dependencies(self, project_path: str) -> bool:
        """
        Install dependencies for a project to enable vulnerability scanning.
        
        Args:
            project_path: Path to the project directory.
            
        Returns:
            True if dependencies were installed successfully, False otherwise.
        """
        try:
            # Check for different dependency files and install accordingly
            dependency_files = {
                "requirements.txt": ["python3", "-m", "pip", "install", "-r", "requirements.txt"],
                "package.json": ["npm", "install"],
                "Gemfile": ["bundle", "install"],
                "pom.xml": ["mvn", "dependency:resolve"],
                "build.gradle": ["gradle", "dependencies"],
                "Cargo.toml": ["cargo", "build"],
                "go.mod": ["go", "mod", "download"],
                "composer.json": ["composer", "install"],
                "Pipfile": ["pipenv", "install"],
                "poetry.lock": ["poetry", "install"],
                "yarn.lock": ["yarn", "install"]
            }
            
            installed_any = False
            
            for dep_file, install_cmd in dependency_files.items():
                dep_file_path = os.path.join(project_path, dep_file)
                if os.path.exists(dep_file_path):
                    logger.info(f"Found {dep_file}, installing dependencies...")
                    
                    # Run the install command
                    result = await self._run_dependency_command(install_cmd, project_path)
                    
                    if result["success"]:
                        logger.info(f"Successfully installed dependencies from {dep_file}")
                        installed_any = True
                    else:
                        logger.warning(f"Failed to install dependencies from {dep_file}: {result.get('stderr', 'Unknown error')}")
                        # Continue trying other dependency files
                        
            return installed_any
            
        except Exception as e:
            logger.warning(f"Error installing dependencies: {e}")
            return False
    
    async def _run_dependency_command(
        self, 
        cmd: List[str], 
        cwd: str, 
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Run a dependency installation command asynchronously.
        
        Args:
            cmd: Command arguments.
            cwd: Working directory.
            timeout: Command timeout in seconds.
            
        Returns:
            Dict containing command result.
        """
        try:
            logger.debug(f"Running dependency command: {' '.join(cmd)} in {cwd}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                
                return {
                    "success": process.returncode == 0,
                    "stdout": stdout.decode('utf-8', errors='replace'),
                    "stderr": stderr.decode('utf-8', errors='replace'),
                    "returncode": process.returncode
                }
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout} seconds",
                    "returncode": -1
                }
                
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
    
    def _parse_scan_output(self, json_output: str) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Parse Snyk JSON output to extract vulnerabilities and summary.
        
        Args:
            json_output: Raw JSON output from Snyk.
            
        Returns:
            Tuple of (vulnerabilities list, summary dict).
        """
        try:
            data = json.loads(json_output)
            
            vulnerabilities = []
            summary = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "total": 0
            }
            
            # Handle different JSON structures
            if isinstance(data, list):
                # Multiple projects in the scan
                for project_data in data:
                    vulns, proj_summary = self._extract_vulnerabilities_from_project(project_data)
                    vulnerabilities.extend(vulns)
                    for severity in summary:
                        if severity in proj_summary:
                            summary[severity] += proj_summary[severity]
            elif isinstance(data, dict):
                # Single project scan
                vulnerabilities, summary = self._extract_vulnerabilities_from_project(data)
            
            return vulnerabilities, summary
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Snyk JSON output: {e}")
            return [], {"error": "Failed to parse JSON output"}
        except Exception as e:
            logger.error(f"Error parsing scan output: {e}")
            return [], {"error": str(e)}
    
    def _extract_vulnerabilities_from_project(self, project_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Extract vulnerabilities from a single project's scan data.
        
        Args:
            project_data: Project scan data from Snyk JSON.
            
        Returns:
            Tuple of (vulnerabilities list, summary dict).
        """
        vulnerabilities = []
        summary = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "total": 0
        }
        
        # Extract vulnerabilities from different sections
        vuln_sources = ["vulnerabilities", "issues"]
        
        for source in vuln_sources:
            if source in project_data:
                for vuln in project_data[source]:
                    processed_vuln = self._process_vulnerability(vuln)
                    vulnerabilities.append(processed_vuln)
                    
                    severity = processed_vuln.get("severity", "low").lower()
                    if severity in summary:
                        summary[severity] += 1
                    summary["total"] += 1
        
        return vulnerabilities, summary
    
    def _process_vulnerability(self, vuln_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and normalize vulnerability data.
        
        Args:
            vuln_data: Raw vulnerability data from Snyk.
            
        Returns:
            Processed vulnerability data.
        """
        return {
            "id": vuln_data.get("id", "N/A"),
            "title": vuln_data.get("title", "Unknown vulnerability"),
            "severity": vuln_data.get("severity", "unknown"),
            "type": vuln_data.get("type", "unknown"),
            "package": vuln_data.get("packageName", vuln_data.get("package", "unknown")),
            "version": vuln_data.get("version", "unknown"),
            "description": vuln_data.get("description", ""),
            "cvss_score": vuln_data.get("cvssScore", 0),
            "cve": vuln_data.get("identifiers", {}).get("CVE", []) if vuln_data.get("identifiers") else [],
            "cwe": vuln_data.get("identifiers", {}).get("CWE", []) if vuln_data.get("identifiers") else [],
            "references": vuln_data.get("references", []),
            "introduced_through": vuln_data.get("from", []),
            "upgrade_path": vuln_data.get("upgradePath", []),
            "is_patchable": vuln_data.get("isPatchable", False),
            "is_upgradeable": vuln_data.get("isUpgradable", False),
            "exploit_maturity": vuln_data.get("exploitMaturity", "unknown"),
            "language": vuln_data.get("language", "unknown"),
            "package_manager": vuln_data.get("packageManager", "unknown")
        }
