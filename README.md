# Agent Hub Platform

Agent Hub is a comprehensive AI-powered platform that enables developers and DevOps engineers to interact with intelligent agents through a natural language chat interface. Built on the Model Context Protocol (MCP), it provides seamless integration with tools like GitHub, Azure, Docker, and various utility services to automate tasks and boost productivity from a unified hub.

## 🏗️ Architecture

The Agent Hub platform consists of three main components:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Agent Hub     │    │  Agent Hub API   │    │ MCP Tools Server│
│   (Frontend)    │◄──►│   (Backend)      │◄──►│   (MCP Server)  │
│                 │    │                  │    │                 │
│ Angular 20.1.5+ │    │ FastAPI + Azure  │    │ FastMCP Tools   │
│ TypeScript      │    │ OpenAI + MCP     │    │ Security, PDF,  │
│ Chat Interface  │    │ Multi-Agent      │    │ Web Scraping    │
│                 │    │ Orchestration    │    │ & Utilities     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Components Overview

- **🖥️ Agent Hub (Frontend)**: Angular-based web application providing an intuitive chat interface
- **🚀 Agent Hub API (Backend)**: FastAPI-powered multi-agent orchestration layer with Azure OpenAI integration
- **🔧 MCP Tools Server**: Extensible MCP server providing utility tools for text processing, security analysis, PDF operations, and web scraping

---

## 📋 Prerequisites

- **Node.js** 18+ (for frontend)
- **Python** 3.12+ (for backend and MCP server)
- **Angular CLI** 20.1.5+ 
- **uv** (recommended Python package manager) or pip
- **Azure OpenAI** resource with deployed model
- **Docker** (optional, for containerized deployment)

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd mb-mcp-agent
```

### 2. Environment Configuration

Create `.env` files for each component:

#### Agent Hub API (.env)
```bash
# Copy the example environment file
cp .env.example agent-hub-api/.env

# Edit with your Azure OpenAI credentials
cat > agent-hub-api/.env << EOF
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://genai-nexus.int.api.corpinter.net/apikey/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-10-21
EOF
```

#### MCP Tools Server (.env) - Optional for Authentication
```bash
cat > mcp-tools-server/.env << EOF
MCP_AUTH_ENABLED=true
MCP_AUTH_METHOD=bearer
MCP_PUBLIC_KEY=keys/public.pem
MCP_TOKEN_ISSUER=local-auth
MCP_TOKEN_AUDIENCE=fastmcp-tools
MCP_REQUIRED_SCOPES=read
EOF
```

### 3. Installation & Setup

#### Install All Components
```bash
# Frontend (Agent Hub)
cd agent-hub
npm install
cd ..

# Backend API
cd agent-hub-api
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv sync
cd ..

# MCP Tools Server
cd mcp-tools-server
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv sync
cd ..
```

### 4. Run the Platform

#### Option A: Development Mode (Recommended)

Start each component in separate terminals:

```bash
# Terminal 1: MCP Tools Server
cd mcp-tools-server
source .venv/bin/activate
uv run python main.py
# Server running on http://localhost:3001

# Terminal 2: Agent Hub API
cd agent-hub-api
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
# API running on http://localhost:8000

# Terminal 3: Agent Hub Frontend
cd agent-hub
ng serve
# Frontend running on http://localhost:4200
```

#### Option B: Docker Deployment

```bash
# Build and run MCP Tools Server
cd mcp-tools-server
docker build -t mcp-tools-server .
docker run --rm -p 3001:3001 mcp-tools-server

# Build and run Agent Hub API
cd ../agent-hub-api
docker build -t agent-hub-api .
docker run --rm -p 8000:8000 --env-file .env agent-hub-api

# Build and run Agent Hub Frontend
cd ../agent-hub
docker build -t agent-hub .
docker run --rm -p 4200:4200 agent-hub
```

---

## 🛠️ Development

### Agent Hub (Frontend)

The Angular frontend provides the user interface for interacting with AI agents.

#### Key Commands
```bash
cd agent-hub

# Development server
ng serve

# Generate components
ng generate component component-name

# Build for production
ng build

# Run tests
ng test

# Run e2e tests
ng e2e
```

#### Project Structure
```
agent-hub/
├── src/
│   ├── app/           # Angular application modules
│   ├── environments/  # Environment configurations
│   └── model/         # TypeScript models
├── public/            # Static assets
└── angular.json       # Angular CLI configuration
```

### Agent Hub API (Backend)

FastAPI backend that orchestrates AI agents and integrates with Azure OpenAI.

#### Key Features
- Multi-agent orchestration layer
- Azure OpenAI integration
- MCP (Model Context Protocol) support
- RESTful API endpoints
- Activity logging and file management

#### API Endpoints
- `POST /chat` - Main chat interface for AI interactions
- View full API documentation at `http://localhost:8000/docs`

#### Development Commands
```bash
cd agent-hub-api

# Run development server with auto-reload
uvicorn app.main:app --reload --port 8000

# Run tests
pytest

# Create admin user
python create_admin.py
```

### MCP Tools Server

Extensible MCP server providing various utility tools and integrations.

#### Available Tool Categories

1. **Sample Tools** (`sample/`)
   - Word counting, text processing
   - Mathematical operations
   - Health checks

2. **Security Tools** (`security_tools/`)
   - HTTP header analysis
   - SSL/TLS configuration analysis
   - DNS security assessment
   - Comprehensive security scanning

3. **PDF Tools** (`pdf_tools/`)
   - Text extraction
   - Metadata retrieval
   - Page extraction
   - Content searching

4. **Web Scraper Tools** (`web_scraper_tools/`)
   - URL content scraping
   - Metadata extraction
   - Link extraction
   - Content parsing

#### Development Commands
```bash
cd mcp-tools-server

# Run the MCP server
uv run python main.py

# Generate authentication token
uv run python auth/token_generator.py

# Run specific tool server
uv run python -m tools.sample.server
```

#### Adding New Tools

1. Create a new tool directory (e.g., `my_tool/`)
2. Implement MCP tools using `@mcp.tool()`
3. Register in `main.py`
4. Optional: Add script entry in `pyproject.toml`

---

## 🔐 Authentication & Security

### MCP Tools Server Authentication

The MCP Tools Server supports bearer token authentication:

1. Enable authentication in `.env`:
```env
MCP_AUTH_ENABLED=true
MCP_AUTH_METHOD=bearer
```

2. Generate tokens:
```bash
cd mcp-tools-server
uv run python auth/token_generator.py
```

3. Use token in requests:
```http
Authorization: Bearer <your-jwt-token>
```

---

## 📊 Monitoring & Logging

- **Agent Hub API**: Logs stored in `agent-hub-api/logs/`
- **MCP Tools Server**: Configurable logging with Rich console output
- **Activity Tracking**: Built-in activity logging for API operations

---

## 🧪 Testing

### Run All Tests
```bash
# Frontend tests
cd agent-hub && ng test

# Backend tests
cd agent-hub-api && pytest

# MCP Tools tests
cd mcp-tools-server && pytest tests/
```

---

## 📦 Production Deployment

### Environment Variables Checklist

- ✅ Azure OpenAI credentials configured
- ✅ Database connections established  
- ✅ Authentication tokens generated
- ✅ CORS settings configured
- ✅ Production build optimizations enabled

### Docker Compose (Optional)

Create a `docker-compose.yml` for orchestrated deployment:

```yaml
version: '3.8'
services:
  mcp-tools:
    build: ./mcp-tools-server
    ports:
      - "3001:3001"
  
  api:
    build: ./agent-hub-api
    ports:
      - "8000:8000"
    depends_on:
      - mcp-tools
  
  frontend:
    build: ./agent-hub
    ports:
      - "4200:4200"
    depends_on:
      - api
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📚 Additional Resources

### Documentation
- [Angular CLI Reference](https://angular.dev/tools/cli)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Azure OpenAI Service](https://azure.microsoft.com/en-us/products/ai-services/openai-service)

### Component-Specific READMEs
- [Agent Hub Frontend](./agent-hub/README.md)
- [Agent Hub API](./agent-hub-api/README.md)  
- [MCP Tools Server](./mcp-tools-server/README.md)

---

## 📄 License

MIT License - see individual component directories for specific license details.

---

## 🆘 Support & Troubleshooting

### Common Issues

1. **Port Conflicts**: Ensure ports 3001, 8000, and 4200 are available
2. **Python Environment**: Use Python 3.12+ and activate virtual environments
3. **Azure OpenAI**: Verify API keys and endpoint configurations
4. **CORS Issues**: Check backend CORS settings for frontend communication

### Getting Help

- Open an issue on the GitHub repository
- Check component-specific READMEs for detailed troubleshooting
- Review logs in respective `logs/` directories

---

## 🌟 Features

- 🤖 **Multi-Agent Orchestration** - Coordinate multiple AI agents seamlessly
- 🔧 **Extensible Tool Integration** - Easy-to-add MCP tools and services  
- 🌐 **Modern Web Interface** - Responsive Angular frontend with real-time chat
- 🔒 **Enterprise Security** - JWT authentication and security analysis tools
- 📊 **Comprehensive Monitoring** - Activity logging and health checks
- 🐳 **Container Ready** - Docker support for all components
- ⚡ **High Performance** - FastAPI backend with async operations
- 🔌 **Protocol Compliance** - Full Model Context Protocol support

---

**Happy coding! 🚀**