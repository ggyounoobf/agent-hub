"""
Web Scraper MCP Tools Server

This module defines MCP tools for web scraping functionality.
"""

import json
from typing import Any, Dict, List, Optional

from shared.utils.logging import logger

from .services.web_scraper_service import ScrapingConfig, WebScraperService

__version__ = "1.0.0"

# Global scraper service instance
_scraper_service: Optional[WebScraperService] = None


async def get_scraper_service(config: Optional[Dict[str, Any]] = None) -> WebScraperService:
    """Get or create a scraper service instance."""
    global _scraper_service

    if _scraper_service is None:
        scraper_config = ScrapingConfig()

        if config:
            # Apply configuration if provided
            if "timeout" in config:
                scraper_config.timeout = config["timeout"]
            if "user_agent" in config:
                scraper_config.user_agent = config["user_agent"]
            if "blocked_domains" in config:
                scraper_config.blocked_domains = config["blocked_domains"]
            if "extract_content" in config:
                scraper_config.extract_content = config["extract_content"]
            if "extract_metadata" in config:
                scraper_config.extract_metadata = config["extract_metadata"]
            if "extract_links" in config:
                scraper_config.extract_links = config["extract_links"]
            if "extract_images" in config:
                scraper_config.extract_images = config["extract_images"]
            if "extract_tables" in config:
                scraper_config.extract_tables = config["extract_tables"]
            if "extract_structured_data" in config:
                scraper_config.extract_structured_data = config["extract_structured_data"]

        _scraper_service = WebScraperService(scraper_config)

    return _scraper_service


async def cleanup_scraper_service():
    """Cleanup the scraper service."""
    global _scraper_service
    if _scraper_service:
        await _scraper_service.close()
        _scraper_service = None


def register_web_scraper_tools(mcp):
    """
    Register web scraper tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def scrape_url(
        url: str,
        timeout: int = 30,
        user_agent: str = "Mozilla/5.0 (Web Scraper Service/1.0)",
        extract_content: bool = True,
        extract_metadata: bool = True,
        extract_links: bool = True,
        extract_images: bool = True,
        extract_tables: bool = False,
        extract_structured_data: bool = False,
        blocked_domains: Optional[List[str]] = None,
    ) -> str:
        """
        Scrape content from a single URL and extract various data elements.

        Args:
            url: The URL to scrape
            timeout: Request timeout in seconds
            user_agent: User agent string to use
            extract_content: Whether to extract main content
            extract_metadata: Whether to extract metadata
            extract_links: Whether to extract links
            extract_images: Whether to extract images
            extract_tables: Whether to extract tables
            extract_structured_data: Whether to extract structured data
            blocked_domains: List of blocked domains

        Returns:
            JSON string with scraping results
        """
        try:
            logger.info(f"Scraping URL: {url}")

            config = {
                "timeout": timeout,
                "user_agent": user_agent,
                "extract_content": extract_content,
                "extract_metadata": extract_metadata,
                "extract_links": extract_links,
                "extract_images": extract_images,
                "extract_tables": extract_tables,
                "extract_structured_data": extract_structured_data,
                "blocked_domains": blocked_domains or [],
            }

            scraper = await get_scraper_service(config)

            async with scraper:
                result = await scraper.scrape_url(url)

            # Format the result
            response_data = {
                "url": result.url,
                "success": result.success,
                "status_code": result.status_code,
                "response_time": result.response_time,
                "content_length": len(result.content) if result.content else 0,
                "metadata": result.metadata,
                "links_count": len(result.links),
                "images_count": len(result.images),
                "tables_count": len(result.tables),
            }

            if result.success:
                response_data.update(
                    {
                        "content": (
                            result.content[:2000] + "..."
                            if len(result.content) > 2000
                            else result.content
                        ),
                        "links": result.links[:10],  # First 10 links
                        "images": result.images[:10],  # First 10 images
                        "tables": result.tables,
                        "structured_data": result.structured_data,
                    }
                )
            else:
                response_data["error"] = result.error

            return json.dumps(response_data, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error in scrape_url tool: {e}")
            return json.dumps({"url": url, "success": False, "error": str(e)}, indent=2)

    @mcp.tool()
    async def scrape_multiple_urls(
        urls: List[str],
        max_concurrent: int = 10,
        timeout: int = 30,
        extract_content: bool = True,
        extract_metadata: bool = True,
        extract_links: bool = False,
        extract_images: bool = False,
        blocked_domains: Optional[List[str]] = None,
    ) -> str:
        """
        Scrape content from multiple URLs concurrently.

        Args:
            urls: List of URLs to scrape
            max_concurrent: Maximum number of concurrent requests
            timeout: Request timeout in seconds
            extract_content: Whether to extract main content
            extract_metadata: Whether to extract metadata
            extract_links: Whether to extract links
            extract_images: Whether to extract images
            blocked_domains: List of blocked domains

        Returns:
            JSON string with scraping results
        """
        try:
            logger.info(f"Scraping {len(urls)} URLs concurrently")

            config = {
                "timeout": timeout,
                "extract_content": extract_content,
                "extract_metadata": extract_metadata,
                "extract_links": extract_links,
                "extract_images": extract_images,
                "blocked_domains": blocked_domains or [],
            }

            scraper = await get_scraper_service(config)

            async with scraper:
                results = await scraper.scrape_multiple_urls(urls, max_concurrent)

            # Format the results
            response_data = {
                "total_urls": len(urls),
                "successful": sum(1 for r in results if r.success),
                "failed": sum(1 for r in results if not r.success),
                "results": [],
            }

            for result in results:
                result_data = {
                    "url": result.url,
                    "success": result.success,
                    "status_code": result.status_code,
                    "response_time": result.response_time,
                    "content_length": len(result.content) if result.content else 0,
                }

                if result.success:
                    result_data.update(
                        {
                            "title": result.metadata.get("title", "N/A"),
                            "description": result.metadata.get("description", "N/A"),
                            "links_count": len(result.links),
                            "images_count": len(result.images),
                        }
                    )
                else:
                    result_data["error"] = result.error

                response_data["results"].append(result_data)

            return json.dumps(response_data, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error in scrape_multiple_urls tool: {e}")
            return json.dumps({"urls": urls, "success": False, "error": str(e)}, indent=2)

    @mcp.tool()
    async def extract_page_metadata(url: str, timeout: int = 30) -> str:
        """
        Extract only metadata from a webpage (title, description, etc.).

        Args:
            url: The URL to extract metadata from
            timeout: Request timeout in seconds

        Returns:
            JSON string with metadata
        """
        try:
            logger.info(f"Extracting metadata from: {url}")

            config = {
                "timeout": timeout,
                "extract_content": False,
                "extract_metadata": True,
                "extract_links": False,
                "extract_images": False,
            }

            scraper = await get_scraper_service(config)

            async with scraper:
                result = await scraper.scrape_url(url)

            if result.success:
                response_data = {"url": result.url, "success": True, "metadata": result.metadata}
            else:
                response_data = {"url": result.url, "success": False, "error": result.error}

            return json.dumps(response_data, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error in extract_page_metadata tool: {e}")
            return json.dumps({"url": url, "success": False, "error": str(e)}, indent=2)

    @mcp.tool()
    async def extract_page_links(url: str, timeout: int = 30) -> str:
        """
        Extract all links from a webpage.

        Args:
            url: The URL to extract links from
            timeout: Request timeout in seconds

        Returns:
            JSON string with links
        """
        try:
            logger.info(f"Extracting links from: {url}")

            config = {
                "timeout": timeout,
                "extract_content": False,
                "extract_metadata": False,
                "extract_links": True,
                "extract_images": False,
            }

            scraper = await get_scraper_service(config)

            async with scraper:
                result = await scraper.scrape_url(url)

            if result.success:
                response_data = {
                    "url": result.url,
                    "success": True,
                    "links_count": len(result.links),
                    "links": result.links,
                }
            else:
                response_data = {"url": result.url, "success": False, "error": result.error}

            return json.dumps(response_data, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error in extract_page_links tool: {e}")
            return json.dumps({"url": url, "success": False, "error": str(e)}, indent=2)

    @mcp.tool()
    async def extract_page_content(url: str, timeout: int = 30, max_length: int = 5000) -> str:
        """
        Extract only the main content from a webpage.

        Args:
            url: The URL to extract content from
            timeout: Request timeout in seconds
            max_length: Maximum content length to return

        Returns:
            JSON string with content
        """
        try:
            logger.info(f"Extracting content from: {url}")

            config = {
                "timeout": timeout,
                "extract_content": True,
                "extract_metadata": True,  # Include basic metadata
                "extract_links": False,
                "extract_images": False,
            }

            scraper = await get_scraper_service(config)

            async with scraper:
                result = await scraper.scrape_url(url)

            if result.success:
                content = result.content
                if len(content) > max_length:
                    content = content[:max_length] + "..."

                response_data = {
                    "url": result.url,
                    "success": True,
                    "title": result.metadata.get("title", "N/A"),
                    "content_length": len(result.content),
                    "content": content,
                }
            else:
                response_data = {"url": result.url, "success": False, "error": result.error}

            return json.dumps(response_data, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error in extract_page_content tool: {e}")
            return json.dumps({"url": url, "success": False, "error": str(e)}, indent=2)

    logger.info("Web Scraper MCP tools registered")
