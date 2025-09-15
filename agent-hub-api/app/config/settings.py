import os
from enum import Enum
from dotenv import load_dotenv

# Force reload environment variables from .env file
load_dotenv(override=True)

class LLMProvider(Enum):
    AZURE_OPENAI = "azure_openai"
    LLAMA3 = "llama3"
    OLLAMA = "ollama"
    
# LLM Provider Selection
LLM_PROVIDER = LLMProvider(os.getenv("LLM_PROVIDER", "azure_openai"))

# Azure OpenAI configuration
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

# Llama3/Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLAMA3_MODEL = os.getenv("LLAMA3_MODEL", "llama3")
LLAMA3_CONTEXT_WINDOW = int(os.getenv("LLAMA3_CONTEXT_WINDOW", "4096"))

# MCP Server
MCP_URL = os.getenv("MCP_URL", "http://localhost:8000/mcp")
MCP_BEARER_TOKEN = os.getenv("MCP_BEARER_TOKEN", "")

# LLM Settings
LLM_MAX_ITERATIONS = int(os.getenv("LLM_MAX_ITERATIONS", "15"))  # Reverted to moderate limit
LLM_REQUEST_TIMEOUT = float(os.getenv("LLM_REQUEST_TIMEOUT", "120"))  # Use float to handle decimal values
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))  # Reverted to original
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1000"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_REQUEST_TIMEOUT = float(os.getenv("LLM_REQUEST_TIMEOUT", "180.0"))
LLM_MEMORY_TOKEN_LIMIT = int(os.getenv("LLM_MEMORY_TOKEN_LIMIT", "2000"))

# Personal GitHub Access Token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Snyk Configuration
SNYK_TOKEN = os.getenv("SNYK_TOKEN")
SNYK_ORG = os.getenv("SNYK_CFG_ORG")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agent_hub.db")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-make-it-very-secure")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# GitHub OAuth2 Configuration
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/auth/github/callback")

#Azure Credentials
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
AZURE_SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID", "")


# Frontend Configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4200")

# Get allowed origins from environment or use defaults
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:4200,http://localhost:8000").split(",")

def validate_llm_config() -> bool:
    """Validate LLM configuration based on selected provider."""
    if LLM_PROVIDER == LLMProvider.AZURE_OPENAI:
        return all([AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION])
    elif LLM_PROVIDER in [LLMProvider.LLAMA3, LLMProvider.OLLAMA]:
        return bool(OLLAMA_BASE_URL and LLAMA3_MODEL)
    return False

def get_llm_display_name() -> str:
    """Get display name for current LLM provider."""
    if LLM_PROVIDER == LLMProvider.AZURE_OPENAI:
        return f"Azure OpenAI ({AZURE_OPENAI_DEPLOYMENT})"
    elif LLM_PROVIDER in [LLMProvider.LLAMA3, LLMProvider.OLLAMA]:
        return f"Llama3 ({LLAMA3_MODEL})"
    return str(LLM_PROVIDER.value)

__all__ = [
    # LLM Provider
    "LLMProvider",
    "LLM_PROVIDER",
    
    # Azure OpenAI
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT", 
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
    
    # Llama3/Ollama
    "OLLAMA_BASE_URL",
    "LLAMA3_MODEL",
    "LLAMA3_CONTEXT_WINDOW",
    
    # MCP Server
    "MCP_URL",
    "MCP_BEARER_TOKEN",
    
    # LLM Configuration
    "LLM_TEMPERATURE",
    "LLM_MAX_ITERATIONS",
    "LLM_MAX_TOKENS",
    "LLM_MAX_RETRIES", 
    "LLM_REQUEST_TIMEOUT",
    "LLM_MEMORY_TOKEN_LIMIT",

    # GitHub
    "GITHUB_TOKEN",
    
    # Database
    "DATABASE_URL",
    
    # JWT
    "SECRET_KEY",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRE_DAYS",
    
    # GitHub OAuth2
    "GITHUB_CLIENT_ID",
    "GITHUB_CLIENT_SECRET", 
    "GITHUB_REDIRECT_URI",
    
    # Frontend
    "FRONTEND_URL",

    "ALLOWED_ORIGINS",
    
    # Helper functions
    "validate_llm_config",
    "get_llm_display_name",

    #Azure Credentials
    "AZURE_TENANT_ID",
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
    "AZURE_SUBSCRIPTION_ID",
    
    # Snyk Configuration  
    "SNYK_TOKEN",
    "SNYK_ORG",

]