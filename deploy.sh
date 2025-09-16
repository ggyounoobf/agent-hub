#!/bin/bash

# Deployment Script for Agent Hub Platform
# This script deploys the Agent Hub platform to a remote server using Docker Compose

set -e  # Exit on any error

# Configuration
REMOTE_HOST="${REMOTE_HOST:-your-server.com}"
REMOTE_USER="${REMOTE_USER:-deploy}"
REMOTE_PATH="${REMOTE_PATH:-/opt/agent-hub}"
SSH_KEY="${SSH_KEY:-~/.ssh/id_rsa}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Agent Hub Deployment Script ===${NC}"

# Check if required tools are installed
command -v ssh >/dev/null 2>&1 || { echo >&2 -e "${RED}SSH is required but not installed.${NC}"; exit 1; }
command -v rsync >/dev/null 2>&1 || { echo >&2 -e "${RED}rsync is required but not installed.${NC}"; exit 1; }

# Function to print usage
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --host HOST     Remote host to deploy to (default: $REMOTE_HOST)"
    echo "  --user USER     Remote user (default: $REMOTE_USER)"
    echo "  --path PATH     Remote path to deploy to (default: $REMOTE_PATH)"
    echo "  --key KEY       SSH key to use (default: $SSH_KEY)"
    echo "  --env FILE      Environment file to use (default: .env.prod)"
    echo "  --help          Show this help message"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            REMOTE_HOST="$2"
            shift 2
            ;;
        --user)
            REMOTE_USER="$2"
            shift 2
            ;;
        --path)
            REMOTE_PATH="$2"
            shift 2
            ;;
        --key)
            SSH_KEY="$2"
            shift 2
            ;;
        --env)
            ENV_FILE="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option $1${NC}"
            usage
            ;;
    esac
done

# Set default environment file if not specified
ENV_FILE="${ENV_FILE:-.env.prod}"

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Warning: Environment file $ENV_FILE not found${NC}"
    echo -e "${YELLOW}Make sure to create $ENV_FILE with your Azure OpenAI credentials:${NC}"
    echo -e "${YELLOW}AZURE_OPENAI_API_KEY=your-key${NC}"
    echo -e "${YELLOW}AZURE_OPENAI_ENDPOINT=your-endpoint${NC}"
    echo -e "${YELLOW}AZURE_OPENAI_DEPLOYMENT=your-deployment${NC}"
    echo -e "${YELLOW}AZURE_OPENAI_API_VERSION=2024-10-21${NC}"
    echo ""
    read -p "Do you want to continue without environment file? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create deployment directory
echo -e "${GREEN}Creating deployment directory on remote server...${NC}"
ssh -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_PATH"

# Copy docker-compose file
echo -e "${GREEN}Copying docker-compose.yml to remote server...${NC}"
rsync -avz -e "ssh -i $SSH_KEY" ./docker-compose.yml "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/"

# Copy environment file if it exists
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}Copying $ENV_FILE to remote server...${NC}"
    rsync -avz -e "ssh -i $SSH_KEY" "$ENV_FILE" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/.env"
else
    echo -e "${YELLOW}Skipping environment file copy (file not found)${NC}"
fi

# Deploy using Docker Compose on remote server
echo -e "${GREEN}Deploying services on remote server...${NC}"
ssh -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" "
    cd $REMOTE_PATH && \
    echo 'Pulling latest images...' && \
    docker-compose pull && \
    echo 'Stopping existing services...' && \
    docker-compose down && \
    echo 'Starting services...' && \
    docker-compose up -d && \
    echo 'Waiting for services to start...' && \
    sleep 10 && \
    echo 'Checking service status...' && \
    docker-compose ps
"

echo -e "${GREEN}Deployment completed!${NC}"
echo -e "${GREEN}Services should be available at:${NC}"
echo -e "${GREEN}  Agent Hub Frontend: http://$REMOTE_HOST:4200${NC}"
echo -e "${GREEN}  Agent Hub API: http://$REMOTE_HOST:8000${NC}"
echo -e "${GREEN}  MCP Tools Server: http://$REMOTE_HOST:3001${NC}"

# Show service logs
echo ""
echo -e "${YELLOW}Showing recent logs (press Ctrl+C to exit):${NC}"
ssh -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" "cd $REMOTE_PATH && docker-compose logs --tail=20 -f" || true