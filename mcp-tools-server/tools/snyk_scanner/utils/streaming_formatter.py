"""
Streaming Response Formatter

Specialized formatter for sending incremental scan results via SSE to prevent timeouts.
"""

import json
import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import asdict

from shared.utils.logging import logger


class StreamingResponseFormatter:
    """Handles streaming of scan results to prevent SSE timeouts."""
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_callback = progress_callback
        self.start_time = time.time()
        self.last_update = time.time()
        self.update_interval = 10.0  # Send updates every 10 seconds
        self.heartbeat_interval = 15.0  # Send heartbeat every 15 seconds
        self.last_heartbeat = time.time()
    
    def should_send_update(self) -> bool:
        """Check if enough time has passed to send an update."""
        current_time = time.time()
        return (current_time - self.last_update) >= self.update_interval
    
    def should_send_heartbeat(self) -> bool:
        """Check if enough time has passed to send a heartbeat."""
        current_time = time.time()
        return (current_time - self.last_heartbeat) >= self.heartbeat_interval
    
    def send_heartbeat(self):
        """Send a heartbeat to keep SSE connection alive."""
        if self.progress_callback and self.should_send_heartbeat():
            elapsed = time.time() - self.start_time
            heartbeat_data = {
                "type": "heartbeat",
                "elapsed_seconds": round(elapsed, 1),
                "message": f"⏳ Scan in progress... ({elapsed:.0f}s elapsed)",
                "timestamp": time.strftime("%H:%M:%S"),
                "status": "alive"
            }
            
            self.progress_callback(f"⏳ Scan in progress... ({elapsed:.0f}s elapsed)", "heartbeat", heartbeat_data)
            self.last_heartbeat = time.time()
    
    def send_progress_update(self, message: str, data: Optional[Dict] = None):
        """Send a progress update if callback is available and enough time has passed."""
        if self.progress_callback:
            elapsed = time.time() - self.start_time
            update_data = {
                "type": "progress_update",
                "elapsed_seconds": round(elapsed, 1),
                "message": message,
                "timestamp": time.strftime("%H:%M:%S")
            }
            if data:
                update_data.update(data)
            
            self.progress_callback(message, "streaming_update", update_data)
            self.last_update = time.time()
            
        # Also send heartbeat if needed
        self.send_heartbeat()
    
    def create_minimal_vulnerability_summary(self, vulnerabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create an extremely minimal vulnerability summary for SSE streaming."""
        if not vulnerabilities:
            return {"total": 0, "summary": "No vulnerabilities found"}
        
        # Count by severity only
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        top_critical = []
        
        for vuln in vulnerabilities[:20]:  # Only process first 20 for speed
            severity = vuln.get("severity", "unknown").lower()
            if severity in severity_counts:
                severity_counts[severity] += 1
            
            # Collect top critical issues (first 3)
            if severity == "critical" and len(top_critical) < 3:
                top_critical.append({
                    "id": vuln.get("id", "unknown")[:20],  # Truncate IDs
                    "title": vuln.get("title", "Unknown")[:50],  # Truncate titles
                    "module": vuln.get("moduleName", vuln.get("packageName", "unknown"))[:30]
                })
        
        return {
            "total": len(vulnerabilities),
            "critical": severity_counts["critical"],
            "high": severity_counts["high"], 
            "medium": severity_counts["medium"],
            "low": severity_counts["low"],
            "top_critical": top_critical,
            "note": f"Showing summary of {min(20, len(vulnerabilities))} vulnerabilities (truncated for SSE)"
        }
    
    def create_streaming_scan_result(self, scan_result, progress_log: List[Dict]) -> Dict[str, Any]:
        """Create a streaming-optimized scan result that's small enough for SSE."""
        
        # Convert scan_result to dict if it's a dataclass
        if hasattr(scan_result, '__dict__'):
            result_dict = asdict(scan_result) if hasattr(scan_result, '__dataclass_fields__') else scan_result.__dict__
        else:
            result_dict = scan_result
        
        # Create minimal result
        minimal_result = {
            "success": result_dict.get("success", False),
            "scan_type": result_dict.get("scan_type", "unknown"),
            "project_path": result_dict.get("project_path", ""),
            "scan_time": result_dict.get("scan_time", time.strftime("%Y-%m-%d %H:%M:%S")),
            "vulnerabilities_summary": self.create_minimal_vulnerability_summary(
                result_dict.get("vulnerabilities", [])
            ),
            "execution_summary": {
                "total_time": round(time.time() - self.start_time, 1),
                "total_steps": len(progress_log),
                "last_update": time.strftime("%H:%M:%S")
            },
            "streaming_info": {
                "response_type": "streaming_optimized",
                "full_details": "Available via detailed scan tool",
                "size_limit": "Optimized for SSE transport"
            }
        }
        
        # Add error if present
        if result_dict.get("error"):
            minimal_result["error"] = str(result_dict["error"])[:200]  # Truncate error messages
        
        # Add condensed progress log (last 5 entries only)
        minimal_result["recent_progress"] = progress_log[-5:] if progress_log else []
        
        return minimal_result
    
    def safe_json_response(self, data: Dict[str, Any], max_size: int = 15000) -> str:
        """
        Create a JSON response that's guaranteed to be under the size limit.
        
        Args:
            data: Response data
            max_size: Maximum size in bytes
            
        Returns:
            JSON string under size limit
        """
        try:
            json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            
            if len(json_str.encode('utf-8')) <= max_size:
                return json_str
            
            # If too large, create emergency minimal response
            logger.warning(f"Response too large ({len(json_str)} chars), creating minimal version")
            
            emergency_response = {
                "success": data.get("success", False),
                "total_vulnerabilities": data.get("vulnerabilities_summary", {}).get("total", 0),
                "critical_count": data.get("vulnerabilities_summary", {}).get("critical", 0),
                "high_count": data.get("vulnerabilities_summary", {}).get("high", 0),
                "execution_time": data.get("execution_summary", {}).get("total_time", 0),
                "message": "Scan completed - response truncated for streaming",
                "note": "Use detailed scan tool for full results"
            }
            
            if data.get("error"):
                emergency_response["error"] = str(data["error"])[:100]
            
            return json.dumps(emergency_response, separators=(',', ':'))
            
        except Exception as e:
            logger.error(f"Error creating JSON response: {e}")
            return json.dumps({
                "success": False,
                "error": f"Response formatting error: {str(e)[:100]}",
                "message": "Scan may have completed but response could not be formatted"
            })


def create_streaming_formatter(progress_callback: Optional[Callable] = None) -> StreamingResponseFormatter:
    """Create a new streaming formatter instance."""
    return StreamingResponseFormatter(progress_callback)
