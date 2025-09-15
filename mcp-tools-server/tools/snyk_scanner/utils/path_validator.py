"""
Path Validation Utilities

Utilities for validating project paths and repository URLs.
"""

import os
import re
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

from shared.utils.logging import logger


def is_valid_path(path: str) -> bool:
    """
    Check if a path is valid and accessible.
    
    Args:
        path: The file system path to validate.
        
    Returns:
        bool: True if the path is valid and accessible, False otherwise.
    """
    try:
        if not path or not isinstance(path, str):
            return False
        
        path_obj = Path(path)
        
        # Check if path exists and is accessible
        return path_obj.exists() and os.access(path, os.R_OK)
        
    except (OSError, ValueError):
        return False


def is_valid_github_url(url: str) -> bool:
    """
    Check if a URL is a valid GitHub repository URL.
    
    Args:
        url: The URL to validate.
        
    Returns:
        bool: True if the URL is a valid GitHub repo URL, False otherwise.
    """
    try:
        if not url or not isinstance(url, str):
            return False
        
        parsed = urlparse(url.strip())
        
        # Check if it's a GitHub URL
        if parsed.netloc.lower() not in ["github.com", "www.github.com"]:
            return False
        
        # Check path format (should be /owner/repo or /owner/repo.git)
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) < 2:
            return False
        
        # Basic validation of owner and repo names
        owner, repo = path_parts[0], path_parts[1]
        
        # Remove .git suffix if present
        if repo.endswith(".git"):
            repo = repo[:-4]
        
        # GitHub username/repo validation (simplified)
        valid_name_pattern = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-_])*[a-zA-Z0-9]$|^[a-zA-Z0-9]$")
        
        return (
            len(owner) <= 39 and 
            len(repo) <= 100 and 
            valid_name_pattern.match(owner) and 
            valid_name_pattern.match(repo)
        )
        
    except Exception as e:
        logger.error(f"Error validating GitHub URL {url}: {e}")
        return False


def extract_repo_info(github_url: str) -> Optional[Tuple[str, str]]:
    """
    Extract owner and repository name from a GitHub URL.
    
    Args:
        github_url: GitHub repository URL.
        
    Returns:
        Tuple of (owner, repo) or None if invalid.
    """
    try:
        if not is_valid_github_url(github_url):
            return None
        
        parsed = urlparse(github_url.strip())
        path_parts = [part for part in parsed.path.split("/") if part]
        
        owner = path_parts[0]
        repo = path_parts[1]
        
        # Remove .git suffix if present
        if repo.endswith(".git"):
            repo = repo[:-4]
        
        return owner, repo
        
    except Exception as e:
        logger.error(f"Error extracting repo info from {github_url}: {e}")
        return None


def normalize_path(path: str) -> str:
    """
    Normalize a file system path.
    
    Args:
        path: The path to normalize.
        
    Returns:
        Normalized absolute path.
    """
    try:
        return str(Path(path).resolve())
    except Exception:
        return path


def is_project_directory(path: str) -> bool:
    """
    Check if a directory contains typical project files that Snyk can scan.
    
    Args:
        path: Directory path to check.
        
    Returns:
        bool: True if directory contains scannable project files.
    """
    try:
        if not is_valid_path(path) or not os.path.isdir(path):
            return False
        
        # Common project files that Snyk can scan
        project_files = [
            "package.json",      # Node.js
            "yarn.lock",         # Yarn
            "package-lock.json", # NPM
            "Pipfile",           # Python Pipenv
            "requirements.txt",  # Python pip
            "pyproject.toml",    # Python
            "Gemfile",           # Ruby
            "pom.xml",           # Java Maven
            "build.gradle",      # Java/Kotlin Gradle
            "build.gradle.kts",  # Kotlin Gradle
            "go.mod",            # Go
            "composer.json",     # PHP
            "packages.config",   # .NET NuGet
            "*.csproj",          # .NET Core
            "*.fsproj",          # F#
            "*.vbproj",          # VB.NET
            "Cargo.toml",        # Rust
            "pubspec.yaml",      # Dart/Flutter
            "mix.exs",           # Elixir
            "rebar.config",      # Erlang
        ]
        
        path_obj = Path(path)
        
        # Check for exact matches
        for filename in project_files:
            if "*" not in filename:
                if (path_obj / filename).exists():
                    return True
        
        # Check for pattern matches (like *.csproj)
        for pattern in project_files:
            if "*" in pattern:
                if list(path_obj.glob(pattern)):
                    return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking if {path} is a project directory: {e}")
        return False


def get_project_type(path: str) -> str:
    """
    Determine the project type based on files present in the directory.
    
    Args:
        path: Directory path to analyze.
        
    Returns:
        String describing the project type.
    """
    try:
        if not is_valid_path(path) or not os.path.isdir(path):
            return "unknown"
        
        path_obj = Path(path)
        
        # Check for specific project types
        if (path_obj / "package.json").exists():
            return "node.js"
        elif (path_obj / "requirements.txt").exists() or (path_obj / "pyproject.toml").exists():
            return "python"
        elif (path_obj / "Gemfile").exists():
            return "ruby"
        elif (path_obj / "pom.xml").exists():
            return "java-maven"
        elif (path_obj / "build.gradle").exists() or (path_obj / "build.gradle.kts").exists():
            return "java-gradle"
        elif (path_obj / "go.mod").exists():
            return "go"
        elif (path_obj / "composer.json").exists():
            return "php"
        elif list(path_obj.glob("*.csproj")) or list(path_obj.glob("*.fsproj")) or list(path_obj.glob("*.vbproj")):
            return "dotnet"
        elif (path_obj / "Cargo.toml").exists():
            return "rust"
        elif (path_obj / "pubspec.yaml").exists():
            return "dart-flutter"
        elif (path_obj / "mix.exs").exists():
            return "elixir"
        else:
            return "mixed"
        
    except Exception as e:
        logger.error(f"Error determining project type for {path}: {e}")
        return "unknown"


def clean_path(path: str) -> str:
    """
    Clean and validate a path string.
    
    Args:
        path: The path to clean.
        
    Returns:
        Cleaned path string.
    """
    if not path:
        return ""
    
    # Remove leading/trailing whitespace
    path = path.strip()
    
    # Remove quotes if present
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    elif path.startswith("'") and path.endswith("'"):
        path = path[1:-1]
    
    return path
