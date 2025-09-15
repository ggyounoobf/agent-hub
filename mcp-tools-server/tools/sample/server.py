"""
Model Context Protocol (MCP) Sample Tool Server implementation.

This module sets up an MCP-compliant server and registers sample tools
that follow Anthropic's Model Context Protocol specification. These tools can be
accessed by Claude and other MCP-compatible AI models to demonstrate basic
MCP functionality and serve as a reference implementation.
"""

from . import __version__
from .utils.logging import logger


def register_sample_tools(mcp):
    """
    Register all tools with the MCP server following the Model Context Protocol specification.

    Each tool is decorated with @mcp.tool() to make it available via the MCP interface.

    Args:
        mcp: The MCP server instance
    """

    @mcp.tool(name="sample_countwords", description="Count the number of words in a sentence.")
    def countwords(sentence: str) -> dict:
        """
        Counts the number of words in a given sentence.

        Words are determined by splitting on whitespace.

        Example:
            countwords("The quick brown fox") => 4
        """
        try:
            if not sentence or not sentence.strip():
                return {"word_count": 0}
            return {"word_count": len(sentence.split())}
        except Exception as e:
            logger.error(f"Error counting words: {e}")
            return {"error": str(e)}

    @mcp.tool(
        name="sample_combineanimals",
        description="Combine two animal names into a hybrid name like 'Lion-Eagle Fusion'.",
    )
    def combineanimals(animal1: str, animal2: str) -> dict:
        """
        Combines the names of two animals into a single hybrid name.

        Example:
            combineanimals("lion", "eagle") => "Lion-Eagle Fusion"
        """
        if not animal1 or not animal2:
            return {"error": "Both animal names are required"}
        return {"result": f"{animal1.capitalize()}-{animal2.capitalize()} Fusion"}

    @mcp.tool(
        name="sample_hello_world",
        description="Return a greeting message. Defaults to 'World' if no name is provided.",
    )
    def hello_world(name: str = "World") -> dict:
        """A simple hello world tool."""
        return {"message": f"Hello, {name}!"}

    @mcp.tool(name="add", description="Add two integers and return the result.")
    def add(a: int, b: int) -> dict:
        """Add two numbers."""
        try:
            return {"result": a + b}
        except Exception as e:
            logger.error(f"Error adding numbers: {e}")
            return {"error": str(e)}

    @mcp.tool(
        name="sample_tool_server_status",
        description="Check if the MCP Sample Tool server is online and get its version.",
    )
    def sample_tool_server_status() -> dict:
        """
        Check if the Model Context Protocol Sample Tool server is running.

        This MCP tool provides a simple way to verify the server is operational.

        Returns:
            A status message indicating the server is online
        """
        return {
            "status": "online",
            "message": "MCP Sample Tool server is running",
            "version": __version__,
        }

    @mcp.prompt()
    def review_code(code: str) -> str:
        return f"Please review this code:\n\n{code}"

    logger.debug("Model Context Protocol Sample Tool registered")
