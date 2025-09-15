"""
URL Validator Utilities

Utilities for validating and processing URLs.
"""

import ipaddress
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from shared.utils.logging import logger


def is_valid_ip(ip_str: str) -> bool:
    """
    Check if a string is a valid IP address.

    Args:
        ip_str: The string to check.

    Returns:
        bool: True if valid IP, False otherwise.
    """
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False


def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid and well-formed.

    Args:
        url: The URL to validate.

    Returns:
        bool: True if the URL is valid, False otherwise.
    """
    try:
        if not url or not isinstance(url, str):
            return False

        parsed = urlparse(url.strip())

        # Check if scheme and netloc exist
        if not parsed.scheme or not parsed.netloc:
            return False

        # Only allow http/https schemes
        if parsed.scheme.lower() not in ["http", "https"]:
            return False

        # Extract hostname (remove port)
        hostname = parsed.netloc.lower()
        if ":" in hostname:
            hostname = hostname.split(":")[0]

        # Validate hostname: localhost, IP address, or domain with dots
        if (
            hostname == "localhost"
            or is_valid_ip(hostname)
            or ("." in hostname and len(hostname) > 1)
        ):
            return True

        return False

    except Exception as e:
        logger.error(f"Error validating URL '{url}': {e}")
        return False


def normalize_url(base_url: str, relative_url: str) -> str:
    """
    Normalize a relative URL to an absolute URL.

    Args:
        base_url: The base URL.
        relative_url: The relative URL to normalize.

    Returns:
        str: The normalized absolute URL.
    """
    try:
        return urljoin(base_url, relative_url)
    except Exception as e:
        logger.error(f"Error normalizing URL '{relative_url}' with base '{base_url}': {e}")
        return ""


def is_allowed_domain(url: str, blocked_domains: list[str]) -> bool:
    """
    Check if a URL is allowed based on blocked domains.

    Args:
        url: The URL to check.
        blocked_domains: A list of blocked domains.

    Returns:
        bool: True if the URL is allowed, False otherwise.
    """
    try:
        if not url:
            return False

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove port if present
        if ":" in domain:
            domain = domain.split(":")[0]

        for blocked in blocked_domains:
            blocked_lower = blocked.lower().strip()
            if not blocked_lower:
                continue

            # Exact match or subdomain match
            if domain == blocked_lower or domain.endswith(f".{blocked_lower}"):
                return False

        return True

    except Exception as e:
        logger.error(f"Error checking domain for URL '{url}': {e}")
        return False


def is_valid_domain_name(domain: str) -> bool:
    """
    Validate if a domain name is properly formatted.

    Args:
        domain: The domain name to validate.

    Returns:
        bool: True if valid domain format, False otherwise.
    """
    try:
        if not domain or len(domain) > 253:
            return False

        # Remove port if present
        if ":" in domain:
            domain = domain.split(":")[0]

        # Special cases
        if domain.lower() == "localhost":
            return True

        # Check if it's an IP address
        if is_valid_ip(domain):
            return True

        # Domain name validation
        if not domain or domain.startswith(".") or domain.endswith("."):
            return False

        # Must contain at least one dot for regular domains
        if "." not in domain:
            return False

        # Check each label
        labels = domain.split(".")
        for label in labels:
            if not label or len(label) > 63:
                return False
            if label.startswith("-") or label.endswith("-"):
                return False
            if not label.replace("-", "").replace("_", "").isalnum():
                return False

        return True

    except Exception as e:
        logger.error(f"Error validating domain '{domain}': {e}")
        return False


def extract_domain(url: str) -> str:
    """
    Extract the domain from a URL.

    Args:
        url: The URL to extract domain from.

    Returns:
        str: The domain, or empty string if invalid.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove port if present
        if ":" in domain:
            domain = domain.split(":")[0]

        return domain

    except Exception as e:
        logger.error(f"Error extracting domain from URL '{url}': {e}")
        return ""


def is_same_domain(url1: str, url2: str) -> bool:
    """
    Check if two URLs belong to the same domain.

    Args:
        url1: First URL.
        url2: Second URL.

    Returns:
        bool: True if same domain, False otherwise.
    """
    try:
        domain1 = extract_domain(url1)
        domain2 = extract_domain(url2)

        # Explicit boolean check to avoid type issues
        if not domain1 or not domain2:
            return False

        return domain1 == domain2

    except Exception as e:
        logger.error(f"Error comparing domains for URLs '{url1}' and '{url2}': {e}")
        return False


def clean_url(url: str) -> str:
    """
    Clean and normalize a URL by removing fragments and common tracking parameters.

    Args:
        url: The URL to clean.

    Returns:
        str: The cleaned URL.
    """
    try:
        parsed = urlparse(url.strip())

        # Remove fragment
        cleaned = parsed._replace(fragment="")

        # Remove common tracking parameters
        if cleaned.query:
            params = parse_qs(cleaned.query)

            # Extended tracking parameters to remove
            tracking_params = {
                # UTM parameters
                "utm_source",
                "utm_medium",
                "utm_campaign",
                "utm_term",
                "utm_content",
                "utm_id",
                "utm_source_platform",
                # Social media tracking
                "fbclid",
                "igshid",
                "tt_medium",
                "tt_content",
                # Google tracking
                "gclid",
                "gclsrc",
                "gbraid",
                "wbraid",
                "_ga",
                "_gl",
                # Email marketing
                "mc_eid",
                "mc_cid",
                "email",
                "e",
                # General tracking
                "ref",
                "referrer",
                "source",
                "campaign_id",
                "ad_id",
                # Analytics platforms
                "_hsenc",
                "_hsmi",
                "hsCtaTracking",
            }

            # Filter out tracking parameters
            clean_params = {k: v for k, v in params.items() if k not in tracking_params}

            # Only update query if we have clean parameters
            if clean_params:
                cleaned = cleaned._replace(query=urlencode(clean_params, doseq=True))
            else:
                cleaned = cleaned._replace(query="")

        return cleaned.geturl()

    except Exception as e:
        logger.error(f"Error cleaning URL '{url}': {e}")
        return url


def is_robots_txt_url(url: str) -> bool:
    """
    Check if the URL points to a robots.txt file.

    Args:
        url: The URL to check.

    Returns:
        bool: True if it's a robots.txt URL, False otherwise.
    """
    try:
        parsed = urlparse(url.lower())
        return parsed.path.endswith("/robots.txt") or parsed.path == "/robots.txt"

    except Exception as e:
        logger.error(f"Error checking robots.txt URL '{url}': {e}")
        return False


def get_base_url(url: str) -> str:
    """
    Get the base URL (scheme + netloc) from a full URL.

    Args:
        url: The full URL.

    Returns:
        str: The base URL, or empty string if invalid.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        return ""
    except Exception as e:
        logger.error(f"Error extracting base URL from '{url}': {e}")
        return ""


def is_absolute_url(url: str) -> bool:
    """
    Check if a URL is absolute (has scheme and netloc).

    Args:
        url: The URL to check.

    Returns:
        bool: True if absolute, False otherwise.
    """
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception as e:
        logger.error(f"Error checking if URL is absolute '{url}': {e}")
        return False


def get_url_extension(url: str) -> str:
    """
    Get the file extension from a URL path.

    Args:
        url: The URL to extract extension from.

    Returns:
        str: The file extension (without dot), or empty string if none.
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Remove query parameters from path
        if "?" in path:
            path = path.split("?")[0]

        # Extract extension
        if "." in path and "/" not in path.split(".")[-1]:
            extension = path.split(".")[-1]
            # Only return reasonable extensions (no longer than 10 chars)
            if len(extension) <= 10:
                return extension

        return ""

    except Exception as e:
        logger.error(f"Error extracting extension from URL '{url}': {e}")
        return ""
