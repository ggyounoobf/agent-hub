"""
Web Scraper Service

Core web scraping service implementation.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import aiohttp

from shared.utils.logging import logger

from ..utils.html_parser import (
    extract_images,
    extract_links,
    extract_main_content,
    extract_metadata,
    extract_structured_data,
    extract_tables,
)
from ..utils.url_validator import clean_url, extract_domain, is_allowed_domain, is_valid_url


@dataclass
class ScrapingResult:
    """Data class for scraping results."""

    url: str
    status_code: int
    success: bool
    content: str
    metadata: Dict[str, Any]
    links: List[Dict[str, str]]
    images: List[Dict[str, str]]
    tables: List[Dict[str, Any]]
    structured_data: Dict[str, Any]
    error: Optional[str] = None
    response_time: Optional[float] = None


@dataclass
class ScrapingConfig:
    """Configuration for web scraping."""

    timeout: int = 30
    max_redirects: int = 10  # Keep for future use, just don't pass to aiohttp
    user_agent: str = "Mozilla/5.0 (Web Scraper Service/1.0)"
    blocked_domains: List[str] = field(default_factory=list)
    follow_redirects: bool = True
    extract_content: bool = True
    extract_metadata: bool = True
    extract_links: bool = True
    extract_images: bool = True
    extract_tables: bool = False
    extract_structured_data: bool = False

    def __post_init__(self):
        if self.blocked_domains is None:
            self.blocked_domains = []


class WebScraperService:
    """Service class for web scraping operations."""

    def __init__(self, config: Optional[ScrapingConfig] = None):
        """
        Initialize the WebScraperService.

        Args:
            config: Configuration for the scraper service.
        """
        self.config = config or ScrapingConfig()
        self._session: Optional[aiohttp.ClientSession] = None
        logger.info("WebScraperService initialized")

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get the session, ensuring it's not None."""
        if self._session is None:
            raise RuntimeError(
                "Session not initialized. Use async context manager or call _ensure_session first."
            )
        return self._session

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self):
        """Ensure aiohttp session is created."""
        if self._session is None or self._session.closed:
            try:
                connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
                timeout = aiohttp.ClientTimeout(total=self.config.timeout)

                self._session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={"User-Agent": self.config.user_agent},
                )
                logger.debug("Created new aiohttp session")
            except Exception as e:
                logger.error(f"Failed to create aiohttp session: {e}")
                raise RuntimeError("Failed to create HTTP session") from e

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("Closed aiohttp session")

    async def scrape_url(self, url: str) -> ScrapingResult:
        """
        Scrape a single URL and extract all requested data.

        Args:
            url: The URL to scrape.

        Returns:
            ScrapingResult: The scraping results.
        """
        start_time = asyncio.get_event_loop().time()

        # Validate URL
        if not is_valid_url(url):
            logger.error(f"Invalid URL: {url}")
            return ScrapingResult(
                url=url,
                status_code=0,
                success=False,
                content="",
                metadata={},
                links=[],
                images=[],
                tables=[],
                structured_data={},
                error="Invalid URL format",
            )

        # Check if domain is allowed
        if not is_allowed_domain(url, self.config.blocked_domains):
            logger.warning(f"Domain blocked: {extract_domain(url)}")
            return ScrapingResult(
                url=url,
                status_code=0,
                success=False,
                content="",
                metadata={},
                links=[],
                images=[],
                tables=[],
                structured_data={},
                error="Domain is blocked",
            )

        # Clean URL
        clean_url_str = clean_url(url)
        logger.info(f"Scraping URL: {clean_url_str}")

        try:
            await self._ensure_session()

            async with self.session.get(
                clean_url_str, allow_redirects=self.config.follow_redirects
            ) as response:

                response_time = asyncio.get_event_loop().time() - start_time
                status_code = response.status

                # Check if response is successful
                if status_code >= 400:
                    logger.warning(f"HTTP error {status_code} for URL: {clean_url_str}")
                    return ScrapingResult(
                        url=clean_url_str,
                        status_code=status_code,
                        success=False,
                        content="",
                        metadata={},
                        links=[],
                        images=[],
                        tables=[],
                        structured_data={},
                        error=f"HTTP {status_code}",
                        response_time=response_time,
                    )

                # Get HTML content
                html_content = await response.text()
                logger.debug(f"Retrieved {len(html_content)} characters from {clean_url_str}")

                # Extract data based on configuration
                result = await self._extract_data(clean_url_str, html_content, response_time)
                result.status_code = status_code

                logger.info(f"Successfully scraped URL: {clean_url_str}")
                return result

        except asyncio.TimeoutError:
            logger.error(f"Timeout error for URL: {clean_url_str}")
            return ScrapingResult(
                url=clean_url_str,
                status_code=0,
                success=False,
                content="",
                metadata={},
                links=[],
                images=[],
                tables=[],
                structured_data={},
                error="Request timeout",
                response_time=asyncio.get_event_loop().time() - start_time,
            )

        except Exception as e:
            logger.error(f"Error scraping URL {clean_url_str}: {e}")
            return ScrapingResult(
                url=clean_url_str,
                status_code=0,
                success=False,
                content="",
                metadata={},
                links=[],
                images=[],
                tables=[],
                structured_data={},
                error=str(e),
                response_time=asyncio.get_event_loop().time() - start_time,
            )

    async def _extract_data(
        self, url: str, html_content: str, response_time: float
    ) -> ScrapingResult:
        """
        Extract data from HTML content based on configuration.

        Args:
            url: The URL that was scraped.
            html_content: The HTML content.
            response_time: The response time.

        Returns:
            ScrapingResult: The extraction results.
        """
        try:
            # Extract main content
            content = ""
            if self.config.extract_content:
                content = extract_main_content(html_content)
                logger.debug(f"Extracted {len(content)} characters of main content")

            # Extract metadata
            metadata = {}
            if self.config.extract_metadata:
                metadata = extract_metadata(html_content)
                logger.debug(f"Extracted metadata: {list(metadata.keys())}")

            # Extract links
            links = []
            if self.config.extract_links:
                links = extract_links(html_content, url)
                logger.debug(f"Extracted {len(links)} links")

            # Extract images
            images = []
            if self.config.extract_images:
                images = extract_images(html_content, url)
                logger.debug(f"Extracted {len(images)} images")

            # Extract tables
            tables = []
            if self.config.extract_tables:
                tables = extract_tables(html_content)
                logger.debug(f"Extracted {len(tables)} tables")

            # Extract structured data
            structured_data = {}
            if self.config.extract_structured_data:
                structured_data = extract_structured_data(html_content)
                logger.debug(f"Extracted structured data: {list(structured_data.keys())}")

            return ScrapingResult(
                url=url,
                status_code=200,  # Will be set by caller
                success=True,
                content=content,
                metadata=metadata,
                links=links,
                images=images,
                tables=tables,
                structured_data=structured_data,
                response_time=response_time,
            )

        except Exception as e:
            logger.error(f"Error extracting data from HTML: {e}")
            return ScrapingResult(
                url=url,
                status_code=200,  # Will be set by caller
                success=False,
                content="",
                metadata={},
                links=[],
                images=[],
                tables=[],
                structured_data={},
                error=f"Data extraction error: {str(e)}",
                response_time=response_time,
            )

    async def scrape_multiple_urls(
        self, urls: List[str], max_concurrent: int = 10
    ) -> List[ScrapingResult]:
        """
        Scrape multiple URLs concurrently.

        Args:
            urls: List of URLs to scrape.
            max_concurrent: Maximum concurrent requests.

        Returns:
            List[ScrapingResult]: List of scraping results.
        """
        logger.info(
            f"Starting to scrape {len(urls)} URLs with max {max_concurrent} concurrent requests"
        )

        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_with_semaphore(url: str) -> ScrapingResult:
            async with semaphore:
                return await self.scrape_url(url)

        try:
            tasks = [scrape_with_semaphore(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions that occurred
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Exception scraping URL {urls[i]}: {result}")
                    final_results.append(
                        ScrapingResult(
                            url=urls[i],
                            status_code=0,
                            success=False,
                            content="",
                            metadata={},
                            links=[],
                            images=[],
                            tables=[],
                            structured_data={},
                            error=str(result),
                        )
                    )
                else:
                    final_results.append(result)

            successful = sum(1 for r in final_results if r.success)
            logger.info(f"Completed scraping: {successful}/{len(urls)} successful")

            return final_results

        except Exception as e:
            logger.error(f"Error in concurrent scraping: {e}")
            return [
                ScrapingResult(
                    url=url,
                    status_code=0,
                    success=False,
                    content="",
                    metadata={},
                    links=[],
                    images=[],
                    tables=[],
                    structured_data={},
                    error=f"Concurrent scraping error: {str(e)}",
                )
                for url in urls
            ]


# Usage example:
async def example_usage():
    """Example of how to use the WebScraperService."""

    # Configure the scraper
    config = ScrapingConfig(
        timeout=30,
        extract_content=True,
        extract_metadata=True,
        extract_links=True,
        extract_images=True,
        blocked_domains=["malicious-site.com"],
    )

    # Use the scraper
    async with WebScraperService(config) as scraper:
        # Scrape a single URL
        result = await scraper.scrape_url("https://example.com")

        if result.success:
            print(f"Title: {result.metadata.get('title', 'N/A')}")
            print(f"Content length: {len(result.content)}")
            print(f"Links found: {len(result.links)}")
        else:
            print(f"Error: {result.error}")

        # Scrape multiple URLs
        urls = ["https://example.com", "https://httpbin.org/html"]
        results = await scraper.scrape_multiple_urls(urls, max_concurrent=5)

        for result in results:
            print(f"URL: {result.url}, Success: {result.success}")


if __name__ == "__main__":
    asyncio.run(example_usage())
