# MCP Tools Server

A lightweight, extensible Model Context Protocol (MCP) server that provides a collection of utility tools for AI assistants and automated systems. Built with FastMCP, this server offers essential text processing, mathematical operations, and utility functions that can be consumed by any MCP-compatible client.

---

## Quick Start

### Prerequisites
- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`
- Docker (optional, for containerized deployment)

---

## Installation (Manual)

```bash
# Clone the repository
git clone <repository-url>
cd mcp-tools-server

# Create virtual environment
uv venv

# Activate virtual environment (Linux/macOS)
source .venv/bin/activate

# OR (Windows)
.venv\Scripts\activate

# Install dependencies
uv sync

# Run the MCP tool server
uv run python main.py
```

---

## Running with Docker

You can run the MCP Tools Server using Docker for easier deployment:

### Build the Docker image

```bash
docker build -t mcp-tools-server .
```

### Run the container

```bash
docker run --rm -p 3001:3001 mcp-tools-server
```

The server will then be accessible at `http://localhost:3001`.

> **Note:** Make sure your FastMCP server is configured with `host="0.0.0.0"` to allow access from outside the container.

---

## Available Tools

### Sample Tool Server
Located in `sample_tool/`, this server provides:

- **countwords**: Count words in text
- **combineanimals**: Create hybrid animal names
- **hello_world**: Simple greeting tool
- **add**: Mathematical addition
- **server_status**: Health check and version info

### Security Tools
Located in `security_tools/`, this server provides:

- **analyze_headers**: Analyze HTTP security headers
- **analyze_ssl**: Analyze SSL/TLS configuration
- **analyze_dns**: Analyze DNS security configuration
- **quick_scan**: Perform a quick security assessment
- **comprehensive_scan**: Perform comprehensive security assessment

### PDF Tools
Located in `pdf_tools/`, this server provides:

- **extract_text**: Extract text from PDF files
- **get_metadata**: Get metadata from PDF files
- **search_text**: Search for specific text in PDF files
- **extract_pages**: Extract specific pages from PDF files
- **get_page_count**: Get the total number of pages in a PDF file

### Web Scraper Tools
Located in `web_scraper_tools/`, this server provides:

- **scrape_url**: Scrape content from a single URL
- **scrape_multiple_urls**: Scrape content from multiple URLs concurrently
- **extract_page_metadata**: Extract metadata from a webpage
- **extract_page_links**: Extract all links from a webpage
- **extract_page_content**: Extract main content from a webpage

```bash
# Run mcp tools server
uv run python main.py
```

---

## Project Structure

```
mcp-tools-server/
├── sample/              # Sample MCP tool implementation
│   ├── __init__.py
│   ├── server.py            # Main server implementation
│   ├── config.py            # Configuration
│   └── utils/
│       └── logging.py       # Logging setup
├── github/        # Example of another MCP tool
│   └── ...
├── auth/                     # Authentication and token utilities
│   ├── keys
│       └── public.pem        # Public PEM file
│   ├── token_generator.py    # Script to generate JWT tokens
├── security_tools/           # Security tools implementation
│   ├── analyze_headers.py    # Analyze HTTP security headers
│   ├── analyze_ssl.py        # Analyze SSL/TLS configuration
│   ├── analyze_dns.py        # Analyze DNS security configuration
│   ├── quick_scan.py         # Perform a quick security assessment
│   ├── comprehensive_scan.py # Perform comprehensive security assessment
├── pdf_tools/                # PDF tools implementation
│   ├── extract_text.py       # Extract text from PDF files
│   ├── get_metadata.py       # Get metadata from PDF files
│   ├── search_text.py        # Search for specific text in PDF files
│   ├── extract_pages.py      # Extract specific pages from PDF files
│   ├── get_page_count.py     # Get the total number of pages in a PDF file
├── web_scraper_tools/        # Web scraper tools implementation
│   ├── scrape_url.py         # Scrape content from a single URL
│   ├── scrape_multiple_urls.py # Scrape content from multiple URLs concurrently
│   ├── extract_page_metadata.py # Extract metadata from a webpage
│   ├── extract_page_links.py # Extract all links from a webpage
│   ├── extract_page_content.py # Extract main content from a webpage
├── main.py                  # Unified tool server entry point
├── Dockerfile               # Docker image configuration
├── pyproject.toml           # Project configuration
├── README.md                # This file
└── requirements.txt         # Dependencies (if using pip)
```

---

## Connection Types

- **HTTP**: Web-based integration, RESTful-style MCP API via `/sse`
- **Stdio**: CLI-based tool communication (e.g., Claude)

---

## Development

### Adding New Tools

1. Create a new tool directory (e.g., `my_tool/`)
2. Implement your MCP tools using `@mcp.tool()`
3. Register them in `main.py`
4. (Optional) Add a script entry in `pyproject.toml`:

```toml
[project.scripts]
my-tool = "my_tool.server:main"
```

---

## Configuration

Each tool can be configured independently. See individual tool directories for specific configuration options.

---
## Authentication (Bearer Token)

To enable bearer token authentication for the MCP Tools Server:

1. Set the following environment variables in your `.env` file:

```
MCP_AUTH_ENABLED=true
MCP_AUTH_METHOD=bearer
MCP_PUBLIC_KEY=<path to your public PEM file or inline string>
MCP_TOKEN_ISSUER=local-auth
MCP_TOKEN_AUDIENCE=fastmcp-tools
MCP_REQUIRED_SCOPES=read
```

2. The public key used to verify the token must be available in the `keys/public.pem` file or passed directly via `MCP_PUBLIC_KEY`.

3. All requests to the MCP server must include a valid bearer token in the `Authorization` header:

```http
Authorization: Bearer <your-jwt-token>
```

---

## Token Generation

For authenticated environments, generate a bearer token using the built-in script:

```bash
uv run python auth/token_generator.py
```

This will output:

1. A public key in PEM format (used by the server to verify tokens)
2. A JWT token with the following default claims:
   - `subject`: "dev-user"
   - `issuer`: "local-auth"
   - `audience`: "fastmcp-tools"
   - `scopes`: ["read", "write"]
   - `expires_in_seconds`: 3600

> To generate a token that does **not expire**, you can omit the `exp` field (custom logic required) or set an extremely long duration:

```python
expires_in_seconds = 10 * 365 * 24 * 60 * 60  # ~10 years
```

The token can be used in any HTTP client or MCP client by setting the `Authorization` header.

---

## Dependencies

Core dependencies:

- **fastmcp**: MCP server framework
- **rich**: Enhanced logging and console output
- **pydantic**: Data validation
- **python-dotenv**: Environment variable management

---

## MCP Compatibility

This server is compatible with:

- Claude (Anthropic)
- Other MCP-compliant AI models
- Custom MCP clients

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests if applicable
5. Submit a pull request

---

## License

MIT License

---

## Support

For issues and questions, please open an issue on the GitHub repository.