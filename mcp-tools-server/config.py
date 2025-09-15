"""
Configuration settings for MCP Tools Server.

This module provides centralized configuration for all MCP tools
and services in the server.
"""

import os
from typing import Literal, cast

from dotenv import load_dotenv

# Force reload environment variables from .env file
load_dotenv(override=True)

# Type definitions
ConnectionType = Literal["stdio", "sse", "streamable-http"]


def _get_connection_type() -> ConnectionType:
    """Get and validate connection type from environment."""
    conn_type = os.getenv("MCP_CONNECTION_TYPE", "sse")
    print(f"Using connection type: {conn_type}")
    # Validate connection type
    if conn_type not in ["stdio", "sse", "streamable-http"]:
        raise ValueError(
            f"Invalid connection type: {conn_type}. Must be 'stdio', 'sse', or 'streamable-http'"
        )
    return cast(ConnectionType, conn_type)


# Default server settings
DEFAULT_HOST = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
DEFAULT_PORT: int = int(os.getenv("MCP_SERVER_PORT", "3001"))
DEFAULT_CONNECTION_TYPE: ConnectionType = _get_connection_type()

# API Keys (add as needed)
# SERP_API_KEY = os.getenv("SERP_API_KEY")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# GitHub Enterprise API Configuration
GITHUB_API_BASE_URL = os.getenv("GITHUB_API_BASE_URL", "https://github.com/api/v3")
GITHUB_API_TIMEOUT = float(os.getenv("GITHUB_API_TIMEOUT", "30.0"))
GITHUB_PAT = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
GITHUB_SSL_VERIFY = os.getenv("GITHUB_SSL_VERIFY", "true").lower() == "true"

# Web Scraper Configuration
WEB_SCRAPER_USER_AGENT = os.getenv(
    "WEB_SCRAPER_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
)
WEB_SCRAPER_TIMEOUT = float(os.getenv("WEB_SCRAPER_TIMEOUT", "30.0"))
WEB_SCRAPER_MAX_RETRIES = int(os.getenv("WEB_SCRAPER_MAX_RETRIES", "3"))
WEB_SCRAPER_DELAY_BETWEEN_REQUESTS = float(os.getenv("WEB_SCRAPER_DELAY_BETWEEN_REQUESTS", "1.0"))
WEB_SCRAPER_MAX_CONTENT_SIZE = int(os.getenv("WEB_SCRAPER_MAX_CONTENT_SIZE", "10485760"))  # 10MB
WEB_SCRAPER_RESPECT_ROBOTS_TXT = (
    os.getenv("WEB_SCRAPER_RESPECT_ROBOTS_TXT", "true").lower() == "true"
)
WEB_SCRAPER_ENABLE_JAVASCRIPT = (
    os.getenv("WEB_SCRAPER_ENABLE_JAVASCRIPT", "false").lower() == "true"
)
WEB_SCRAPER_SSL_VERIFY = os.getenv("WEB_SCRAPER_SSL_VERIFY", "true").lower() == "true"

# Content filtering settings
WEB_SCRAPER_BLOCKED_DOMAINS = (
    os.getenv("WEB_SCRAPER_BLOCKED_DOMAINS", "").split(",")
    if os.getenv("WEB_SCRAPER_BLOCKED_DOMAINS")
    else []
)
WEB_SCRAPER_ALLOWED_CONTENT_TYPES = os.getenv(
    "WEB_SCRAPER_ALLOWED_CONTENT_TYPES", "text/html,application/xhtml+xml,text/plain"
).split(",")

# Rate limiting
WEB_SCRAPER_MAX_CONCURRENT_REQUESTS = int(os.getenv("WEB_SCRAPER_MAX_CONCURRENT_REQUESTS", "5"))
WEB_SCRAPER_RATE_LIMIT_PER_MINUTE = int(os.getenv("WEB_SCRAPER_RATE_LIMIT_PER_MINUTE", "60"))

# Authentication settings
MCP_AUTH_ENABLED = os.getenv("MCP_AUTH_ENABLED", "true").strip().lower() == "true"
MCP_AUTH_METHOD = os.getenv(
    "MCP_AUTH_METHOD", "bearer"
).strip()  # Should be validated against AuthMethod enum if used
PUBLIC_KEY_PATH = "auth/keys/public.pem"
public_key = ""
try:
    with open(PUBLIC_KEY_PATH, "r") as f:
        public_key = f.read().strip()
except FileNotFoundError:
    public_key = None  # or raise an error if you want to enforce presence

MCP_PUBLIC_KEY = public_key
MCP_TOKEN_ISSUER = os.getenv("MCP_TOKEN_ISSUER", "local-auth")
MCP_TOKEN_AUDIENCE = os.getenv("MCP_TOKEN_AUDIENCE", "fastmcp-tools")
MCP_REQUIRED_SCOPES = os.getenv("MCP_REQUIRED_SCOPES", "read")

# # JWT / Basic Auth credentials
# MCP_JWT_SECRET = os.getenv("MCP_JWT_SECRET", "your-secret-key-change-in-production")
# MCP_USERNAME = os.getenv("MCP_USERNAME")
# MCP_PASSWORD = os.getenv("MCP_PASSWORD")

# Rate limiting for auth middleware
MCP_RATE_LIMIT_ENABLED = os.getenv("MCP_RATE_LIMIT_ENABLED", "true").lower() == "true"
MCP_RATE_LIMIT_RPM = int(os.getenv("MCP_RATE_LIMIT_RPM", "100"))
