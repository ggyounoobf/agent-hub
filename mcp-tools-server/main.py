#!/usr/bin/env python3
"""
MCP Tools Server

Main entry point for the MCP Tools Server.
"""
import asyncio
import sys

from fastmcp import FastMCP
from fastmcp.server.auth import BearerAuthProvider
from rich.console import Console
from rich.traceback import install

from config import (
    DEFAULT_CONNECTION_TYPE,
    DEFAULT_HOST,
    DEFAULT_PORT,
    MCP_AUTH_ENABLED,
    MCP_AUTH_METHOD,
    MCP_PUBLIC_KEY,
    MCP_REQUIRED_SCOPES,
    MCP_TOKEN_AUDIENCE,
    MCP_TOKEN_ISSUER,
)
from tools.pdf.server import register_pdf_tools as pdf_tool_main
from tools.sample.server import register_sample_tools as sample_tool_main
from tools.sample.utils.logging import logger
from tools.security.server import register_security_tools as security_tool_main
from tools.snyk_scanner.server import register_snyk_scanner_tools as snyk_scanner_tool_main
from tools.web_scraper.server import register_web_scraper_tools as web_scraper_tool_main

# Setup rich console and traceback
console = Console()
install()

# === Server Configuration ===


def create_mcp_server(auth_provider=None) -> FastMCP:
    """
    Create and configure the Model Context Protocol server.

    Args:
        auth_provider: Optional authentication provider

    Returns:
        Configured MCP server instance

    Notes:
        Setting host="0.0.0.0" allows the server to listen on all available
        network interfaces, making it accessible from outside the container
        or WSL2 environment (e.g., via a browser on Windows).
    """

    mcp = FastMCP("MCPToolService", auth=auth_provider)

    # Register MCP-compliant tools
    try:
        logger.info("Registering MCP tools...")

        sample_tool_main(mcp)
        logger.info("✅ Sample tools registered")

        # github_tool_main(mcp)
        # logger.info("✅ GitHub tools registered")

        web_scraper_tool_main(mcp)
        logger.info("✅ Web Scraper tools registered")

        pdf_tool_main(mcp)
        logger.info("✅ PDF tools registered")

        security_tool_main(mcp)
        logger.info("✅ Security tools registered")

        snyk_scanner_tool_main(mcp)
        logger.info("✅ Snyk Scanner tools registered")

        logger.info("[green]🎯 All MCP tools registered successfully[/green]")

    except Exception as e:
        logger.error(f"[red]❌ Error registering tools:[/red] {e}")
        raise

    return mcp


async def cleanup_resources():
    """Cleanup all resources when shutting down."""
    try:
        logger.info("🧹 Cleaning up resources...")

        # Cleanup web scraper resources
        from tools.web_scraper.server import cleanup_scraper_service

        await cleanup_scraper_service()
        logger.info("✅ Web scraper resources cleaned up")

        # Add other cleanup calls here as needed
        # await other_tool_cleanup()

        logger.info("[green]✨ All resources cleaned up successfully[/green]")

    except Exception as e:
        logger.error(f"[red]❌ Error during cleanup:[/red] {e}")


def main() -> None:
    """Main entry point for the MCP Tools Server."""
    mcp = None

    try:
        auth_provider = None
        if MCP_AUTH_ENABLED and MCP_AUTH_METHOD.lower() == "bearer":
            logger.info("🔐 Enabling Bearer token authentication")

            if not MCP_PUBLIC_KEY:
                raise ValueError("Bearer auth enabled, but MCP_PUBLIC_KEY is missing")

            auth_provider = BearerAuthProvider(
                public_key=MCP_PUBLIC_KEY,
                issuer=MCP_TOKEN_ISSUER,
                audience=MCP_TOKEN_AUDIENCE,
                required_scopes=MCP_REQUIRED_SCOPES.split(","),
            )
        else:
            logger.info("🔓 Authentication disabled or not set to 'bearer'")

        # Create and configure the MCP server
        mcp = create_mcp_server(auth_provider)

        logger.info("[blue]📋 MCP Tools Server ready with all registered tools[/blue]")

        # Start the server
        mcp.run(transport=DEFAULT_CONNECTION_TYPE, host=DEFAULT_HOST, port=DEFAULT_PORT)

    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Shutting down MCP Tools Server...[/bold yellow]")

    except Exception as e:
        console.print(f"[red]❌ Error running server:[/red] {e}")
        logger.error(f"Server error: {e}")
        sys.exit(1)

    finally:
        # Cleanup resources
        try:
            logger.info("🔄 Starting cleanup process...")
            asyncio.run(cleanup_resources())
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")

        console.print("[bold green]✅ MCP Tools Server shutdown complete[/bold green]")


if __name__ == "__main__":
    main()
