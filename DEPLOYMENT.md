# Deployment Guide for Agent Hub Platform

This guide explains how to deploy the Agent Hub platform using Docker and the provided CI/CD pipeline.

## Prerequisites

1. Docker and Docker Compose installed
2. GitHub Container Registry (GHCR) access (for pre-built images)
3. Azure OpenAI credentials (for agent-hub-api)

## Deployment Options

### Option 1: Using Pre-built Images (Recommended)

1. Create a `.env` file with your configuration:
   ```bash
   # .env
   AZURE_OPENAI_API_KEY=your-azure-openai-key
   AZURE_OPENAI_ENDPOINT=https://your-azure-openai-endpoint
   AZURE_OPENAI_DEPLOYMENT=your-deployment-name
   AZURE_OPENAI_API_VERSION=2024-10-21
   ```

2. Create a `docker-compose.yml` file:
   ```yaml
   version: '3.8'
   
   services:
     mcp-tools-server:
       image: ghcr.io/your-org/agent-hub/mcp-tools-server:latest
       ports:
         - "3001:3001"
       networks:
         - agent-hub-network
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:3001/health"]
         interval: 30s
         timeout: 10s
         retries: 3
         start_period: 40s
   
     agent-hub-api:
       image: ghcr.io/your-org/agent-hub/agent-hub-api:latest
       ports:
         - "8000:8000"
       environment:
         - MCP_TOOLS_SERVER_URL=http://mcp-tools-server:3001
       env_file:
         - .env
       networks:
         - agent-hub-network
       depends_on:
         mcp-tools-server:
           condition: service_healthy
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
         interval: 30s
         timeout: 10s
         retries: 3
         start_period: 40s
   
     agent-hub:
       image: ghcr.io/your-org/agent-hub/agent-hub:latest
       ports:
         - "4200:80"
       networks:
         - agent-hub-network
       depends_on:
         agent-hub-api:
           condition: service_healthy
   
   networks:
     agent-hub-network:
       driver: bridge
   ```

3. Run the platform:
   ```bash
   docker-compose up -d
   ```

### Option 2: Building from Source

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd agent-hub
   ```

2. Create a `.env` file in the root directory with your Azure OpenAI credentials:
   ```bash
   # .env
   AZURE_OPENAI_API_KEY=your-azure-openai-key
   AZURE_OPENAI_ENDPOINT=https://your-azure-openai-endpoint
   AZURE_OPENAI_DEPLOYMENT=your-deployment-name
   AZURE_OPENAI_API_VERSION=2024-10-21
   ```

3. Run with Docker Compose:
   ```bash
   docker-compose up -d --build
   ```

## Accessing the Services

After deployment, you can access the services at:

- Agent Hub Frontend: http://localhost:4200
- Agent Hub API: http://localhost:8000
- MCP Tools Server: http://localhost:3001

## GitHub Actions CI/CD Pipeline

The GitHub Actions workflow (`ci-cd.yml`) in the repository root handles:

1. Building and testing all services on every push/PR
2. Creating Docker images for each service
3. Pushing images to GitHub Container Registry (GHCR)
4. Deployment notifications

### Pipeline Details

- **Build and Test**: Runs on Ubuntu with appropriate environments for each service
- **Docker Build**: Uses Docker Buildx for efficient multi-platform builds
- **Image Tagging**: Automatically tags images with branch names, commit SHA, and semantic versions
- **Deployment**: Triggers on tag pushes (v* pattern) for production deployment

## Customization

You can customize the deployment by:

1. Modifying the `docker-compose.yml` file to change ports or add volumes
2. Creating a `docker-compose.override.yml` file for environment-specific settings
3. Adjusting the `.env` file for different configurations
4. Modifying the GitHub Actions workflow for different deployment targets

## Troubleshooting

1. **Port Conflicts**: Ensure ports 4200, 8000, and 3001 are available
2. **Health Checks**: Check container logs if services fail health checks
3. **Environment Variables**: Verify all required environment variables are set
4. **Network Issues**: Ensure containers can communicate on the shared network