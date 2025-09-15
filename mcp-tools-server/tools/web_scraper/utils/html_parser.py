"""
HTML Parser Utilities

Utilities for parsing and extracting content from HTML.
"""

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from shared.utils.logging import logger


def extract_main_content(html: str) -> str:
    """
    Extract the main text content from an HTML document.

    Args:
        html: The raw HTML content as a string.

    Returns:
        str: The extracted main text content.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove script, style, and other non-content elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()

        # Try to find main content areas first
        main_content = (
            soup.find("main") or soup.find("article") or soup.find("div", class_="content")
        )

        if main_content:
            text = main_content.get_text(separator="\n", strip=True)
        else:
            # Fall back to body content
            body = soup.find("body")
            if body:
                text = body.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error extracting main content: {e}")
        return ""


def extract_metadata(html: str) -> dict:
    """
    Extract metadata (title, description, keywords) from an HTML document.

    Args:
        html: The raw HTML content as a string.

    Returns:
        dict: A dictionary containing metadata.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title = "N/A"
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Extract description
        description = "N/A"
        desc_meta = soup.find("meta", attrs={"name": "description"})
        if desc_meta and isinstance(desc_meta, Tag):
            content = desc_meta.get("content")
            if content:
                description = str(content).strip()

        if description == "N/A":
            # Try property="description" (Open Graph)
            desc_meta = soup.find("meta", attrs={"property": "og:description"})
            if desc_meta and isinstance(desc_meta, Tag):
                content = desc_meta.get("content")
                if content:
                    description = str(content).strip()

        # Extract keywords
        keywords = "N/A"
        keywords_meta = soup.find("meta", attrs={"name": "keywords"})
        if keywords_meta and isinstance(keywords_meta, Tag):
            content = keywords_meta.get("content")
            if content:
                keywords = str(content).strip()

        # Extract additional Open Graph metadata
        og_title = "N/A"
        og_title_meta = soup.find("meta", attrs={"property": "og:title"})
        if og_title_meta and isinstance(og_title_meta, Tag):
            content = og_title_meta.get("content")
            if content:
                og_title = str(content).strip()

        og_type = "N/A"
        og_type_meta = soup.find("meta", attrs={"property": "og:type"})
        if og_type_meta and isinstance(og_type_meta, Tag):
            content = og_type_meta.get("content")
            if content:
                og_type = str(content).strip()

        # Extract charset safely
        charset = "N/A"
        charset_meta = soup.find("meta", attrs={"charset": True})
        if charset_meta and isinstance(charset_meta, Tag):
            charset_value = charset_meta.get("charset")
            if charset_value:
                charset = str(charset_value)

        # Extract viewport safely
        viewport = "N/A"
        viewport_meta = soup.find("meta", attrs={"name": "viewport"})
        if viewport_meta and isinstance(viewport_meta, Tag):
            content = viewport_meta.get("content")
            if content:
                viewport = str(content)

        metadata = {
            "title": title,
            "description": description,
            "keywords": keywords,
            "og_title": og_title,
            "og_type": og_type,
            "charset": charset,
            "viewport": viewport,
        }

        return metadata

    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
        return {
            "title": "N/A",
            "description": "N/A",
            "keywords": "N/A",
            "og_title": "N/A",
            "og_type": "N/A",
            "charset": "N/A",
            "viewport": "N/A",
        }


def extract_links(html: str, base_url: str | None = None) -> list:
    """
    Extract all hyperlinks from an HTML document.

    Args:
        html: The raw HTML content as a string.
        base_url: Base URL to resolve relative links (optional).

    Returns:
        list: A list of dictionaries containing link information.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        links = []

        for link in soup.find_all("a", href=True):
            if not isinstance(link, Tag):
                continue

            # Safe href extraction
            href_attr = link.get("href")
            if not href_attr:
                continue

            # Convert to string and strip
            href = str(href_attr).strip() if href_attr else ""
            if not href:
                continue

            # Safe text extraction
            text = link.get_text(strip=True) or ""

            # Safe title extraction
            title_attr = link.get("title")
            title = str(title_attr).strip() if title_attr else ""

            # Skip empty or invalid links
            if not href or href.startswith(("#", "javascript:", "mailto:")):
                continue

            # Resolve relative URLs if base_url is provided
            if base_url and not urlparse(href).netloc:
                href = urljoin(base_url, href)

            links.append({"href": href, "text": text or "N/A", "title": title or "N/A"})

        return links

    except Exception as e:
        logger.error(f"Error extracting links: {e}")
        return []


def extract_images(html: str, base_url: str | None = None) -> list:
    """
    Extract all image URLs and alt text from an HTML document.

    Args:
        html: The raw HTML content as a string.
        base_url: Base URL to resolve relative image URLs (optional).

    Returns:
        list: A list of dictionaries containing image information.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        images = []

        for img in soup.find_all("img", src=True):
            if not isinstance(img, Tag):
                continue

            # Safe src extraction
            src_attr = img.get("src")
            if not src_attr:
                continue

            src = str(src_attr).strip() if src_attr else ""
            if not src:
                continue

            # Safe alt extraction
            alt_attr = img.get("alt")
            alt = str(alt_attr).strip() if alt_attr else ""

            # Safe title extraction
            title_attr = img.get("title")
            title = str(title_attr).strip() if title_attr else ""

            # Resolve relative URLs if base_url is provided
            if base_url and not urlparse(src).netloc:
                src = urljoin(base_url, src)

            # Safe width/height extraction
            width_attr = img.get("width")
            width = str(width_attr) if width_attr else "N/A"

            height_attr = img.get("height")
            height = str(height_attr) if height_attr else "N/A"

            images.append(
                {
                    "src": src,
                    "alt": alt or "N/A",
                    "title": title or "N/A",
                    "width": width,
                    "height": height,
                }
            )

        return images

    except Exception as e:
        logger.error(f"Error extracting images: {e}")
        return []


def extract_tables(html: str) -> list:
    """
    Extract table data from an HTML document.

    Args:
        html: The raw HTML content as a string.

    Returns:
        list: A list of dictionaries containing table data.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        tables = []

        for table in soup.find_all("table"):
            if not isinstance(table, Tag):
                continue

            table_data = {"headers": [], "rows": [], "caption": ""}

            # Extract caption if present
            caption = table.find("caption")
            if caption and isinstance(caption, Tag):
                table_data["caption"] = caption.get_text(strip=True)

            # Extract headers
            header_row = table.find("tr")
            if header_row and isinstance(header_row, Tag):
                headers = header_row.find_all(["th", "td"])
                table_data["headers"] = [
                    header.get_text(strip=True) for header in headers if isinstance(header, Tag)
                ]

            # Extract all rows
            rows = table.find_all("tr")
            for row in rows[1:]:  # Skip header row
                if not isinstance(row, Tag):
                    continue

                cells = row.find_all(["td", "th"])
                row_data = [cell.get_text(strip=True) for cell in cells if isinstance(cell, Tag)]
                if row_data:  # Only add non-empty rows
                    table_data["rows"].append(row_data)

            if table_data["headers"] or table_data["rows"]:
                tables.append(table_data)

        return tables

    except Exception as e:
        logger.error(f"Error extracting tables: {e}")
        return []


def extract_structured_data(html: str) -> dict:
    """
    Extract structured data (JSON-LD, microdata) from an HTML document.

    Args:
        html: The raw HTML content as a string.

    Returns:
        dict: A dictionary containing structured data.
    """
    try:
        import json

        soup = BeautifulSoup(html, "html.parser")
        structured_data = {"json_ld": [], "microdata": []}

        # Extract JSON-LD
        json_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_scripts:
            if not isinstance(script, Tag) or not script.string:
                continue

            try:
                data = json.loads(script.string)
                structured_data["json_ld"].append(data)
            except (json.JSONDecodeError, AttributeError):
                continue

        # Extract microdata
        microdata_elements = soup.find_all(attrs={"itemscope": True})
        for element in microdata_elements:
            if not isinstance(element, Tag):
                continue

            item = {"type": element.get("itemtype", ""), "properties": {}}

            for prop in element.find_all(attrs={"itemprop": True}):
                if not isinstance(prop, Tag):
                    continue

                prop_name = prop.get("itemprop")
                prop_value = prop.get("content") or prop.get_text(strip=True)
                if prop_name:
                    item["properties"][prop_name] = prop_value

            if item["properties"]:
                structured_data["microdata"].append(item)

        return structured_data

    except Exception as e:
        logger.error(f"Error extracting structured data: {e}")
        return {"json_ld": [], "microdata": []}
