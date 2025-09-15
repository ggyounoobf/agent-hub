"""
Model Context Protocol (MCP) GitHub Tool Server implementation.

This module sets up MCP-compliant GitHub tools that follow Anthropic's
Model Context Protocol specification for GitHub API interactions.
"""

from . import __version__
from .services.github_service import GitHubService
from .utils.logging import logger

# Initialize the GitHub service
github_service = GitHubService()


def register_github_tools(mcp):
    """
    Register all GitHub tools with the MCP server.

    Args:
        mcp: The MCP server instance
    """

    @mcp.tool(
        name="get_github_repository_info", description="Get repository information from GitHub API."
    )
    def get_github_repository_info(owner: str, repo: str) -> dict:
        """
        Get detailed repository information from GitHub.

        Args:
            owner: Repository owner (user or organization)
            repo: Repository name

        Returns:
            dict: Repository information or error details
        """
        logger.info(f"get_github_repository_info called with owner='{owner}', repo='{repo}'")

        try:
            result = github_service.get_repository_info(owner, repo)

            if result.get("success"):
                repo_data = result.get("data", {})

                # Format key repository information
                formatted_repo = {
                    "name": repo_data.get("name", "N/A"),
                    "full_name": repo_data.get("full_name", "N/A"),
                    "description": repo_data.get("description", "No description available"),
                    "language": repo_data.get("language", "Not specified"),
                    "stars": repo_data.get("stargazers_count", 0),
                    "forks": repo_data.get("forks_count", 0),
                    "watchers": repo_data.get("watchers_count", 0),
                    "open_issues": repo_data.get("open_issues_count", 0),
                    "default_branch": repo_data.get("default_branch", "main"),
                    "private": repo_data.get("private", False),
                    "created_at": repo_data.get("created_at", "N/A"),
                    "updated_at": repo_data.get("updated_at", "N/A"),
                    "clone_url": repo_data.get("clone_url", "N/A"),
                    "html_url": repo_data.get("html_url", "N/A"),
                }

                # Create summary
                summary_text = f"""Repository: {formatted_repo['full_name']}
**Description:** {formatted_repo['description']}
**Language:** {formatted_repo['language']}
**Stars:** {formatted_repo['stars']} | **Forks:** {formatted_repo['forks']} | **Watchers:** {formatted_repo['watchers']}
**Open Issues:** {formatted_repo['open_issues']}
**Default Branch:** {formatted_repo['default_branch']}
**Private:** {"Yes" if formatted_repo['private'] else "No"}
**Created:** {formatted_repo['created_at']}
**URL:** {formatted_repo['html_url']}"""

                return {
                    "success": True,
                    "repository": formatted_repo,
                    "raw_data": repo_data,
                    "message": f"Successfully retrieved repository info for {owner}/{repo}",
                    "summary": summary_text,
                }
            else:
                return {
                    "success": False,
                    "repository": None,
                    "error": result.get("error", "Unknown error occurred"),
                    "error_code": result.get("error_code", "UNKNOWN_ERROR"),
                    "message": f"Failed to retrieve repository info for {owner}/{repo}",
                    "summary": f"Error: {result.get('error', 'Unknown error')}",
                }

        except Exception as e:
            logger.error(f"Unexpected error in get_github_repository_info: {e}")
            return {
                "success": False,
                "repository": None,
                "error": f"Tool execution error: {str(e)}",
                "error_code": "TOOL_ERROR",
                "message": "An unexpected error occurred while fetching repository info",
                "summary": f"Tool error: {str(e)}",
            }

    @mcp.tool(name="get_github_rate_limit", description="Get GitHub API rate limit information.")
    def get_github_rate_limit() -> dict:
        """
        Get current GitHub API rate limit status.

        Returns:
            dict: Rate limit information or error details
        """
        logger.info("get_github_rate_limit called")

        try:
            result = github_service.get_rate_limit()

            if result.get("success"):
                rate_data = result.get("data", {})

                # Extract rate limit info
                core_limit = rate_data.get("rate", {})
                search_limit = rate_data.get("resources", {}).get("search", {})

                formatted_limits = {
                    "core": {
                        "limit": core_limit.get("limit", 0),
                        "remaining": core_limit.get("remaining", 0),
                        "reset": core_limit.get("reset", 0),
                        "used": core_limit.get("used", 0),
                    },
                    "search": {
                        "limit": search_limit.get("limit", 0),
                        "remaining": search_limit.get("remaining", 0),
                        "reset": search_limit.get("reset", 0),
                        "used": search_limit.get("used", 0),
                    },
                }

                # Create summary
                summary_text = f"""GitHub API Rate Limits:
**Core API:**
  - Limit: {formatted_limits['core']['limit']} requests/hour
  - Remaining: {formatted_limits['core']['remaining']}
  - Used: {formatted_limits['core']['used']}

**Search API:**
  - Limit: {formatted_limits['search']['limit']} requests/hour
  - Remaining: {formatted_limits['search']['remaining']}
  - Used: {formatted_limits['search']['used']}"""

                return {
                    "success": True,
                    "rate_limits": formatted_limits,
                    "raw_data": rate_data,
                    "message": "Successfully retrieved rate limit information",
                    "summary": summary_text,
                }
            else:
                return {
                    "success": False,
                    "rate_limits": None,
                    "error": result.get("error", "Unknown error occurred"),
                    "error_code": result.get("error_code", "UNKNOWN_ERROR"),
                    "message": "Failed to retrieve rate limit information",
                    "summary": f"Error: {result.get('error', 'Unknown error')}",
                }

        except Exception as e:
            logger.error(f"Unexpected error in get_github_rate_limit: {e}")
            return {
                "success": False,
                "rate_limits": None,
                "error": f"Tool execution error: {str(e)}",
                "error_code": "TOOL_ERROR",
                "message": "An unexpected error occurred while fetching rate limit info",
                "summary": f"Tool error: {str(e)}",
            }

    @mcp.tool(
        name="get_github_repository_branches",
        description="Get repository branches from GitHub API.",
    )
    def get_github_repository_branches(owner: str, repo: str) -> dict:
        """
        Get all branches for a GitHub repository.

        Args:
            owner: Repository owner (user or organization)
            repo: Repository name

        Returns:
            dict: Repository branches or error details
        """
        logger.info(f"get_github_repository_branches called with owner='{owner}', repo='{repo}'")

        try:
            result = github_service.get_repository_branches(owner, repo)

            if result.get("success"):
                branches_data = result.get("data", [])
                count = len(branches_data)

                # Format branch information
                formatted_branches = []
                for branch in branches_data:
                    if isinstance(branch, dict):
                        formatted_branches.append(
                            {
                                "name": branch.get("name", "N/A"),
                                "commit_sha": branch.get("commit", {}).get("sha", "N/A"),
                                "commit_url": branch.get("commit", {}).get("url", "N/A"),
                                "protected": branch.get("protected", False),
                            }
                        )

                # Create summary
                if formatted_branches:
                    summary_lines = [f"Found {count} branches in {owner}/{repo}:\n"]
                    for branch in formatted_branches[:10]:  # Show first 10
                        protection_status = "🔒" if branch["protected"] else "🔓"
                        summary_lines.append(
                            f"  {protection_status} {branch['name']} ({branch['commit_sha'][:8]})"
                        )
                    if count > 10:
                        summary_lines.append(f"  ... and {count - 10} more branches")
                    summary_text = "\n".join(summary_lines)
                else:
                    summary_text = f"No branches found in {owner}/{repo}"

                return {
                    "success": True,
                    "branches": formatted_branches,
                    "count": count,
                    "raw_data": branches_data,
                    "message": f"Successfully retrieved {count} branches for {owner}/{repo}",
                    "summary": summary_text,
                }
            else:
                return {
                    "success": False,
                    "branches": [],
                    "count": 0,
                    "error": result.get("error", "Unknown error occurred"),
                    "error_code": result.get("error_code", "UNKNOWN_ERROR"),
                    "message": f"Failed to retrieve branches for {owner}/{repo}",
                    "summary": f"Error: {result.get('error', 'Unknown error')}",
                }

        except Exception as e:
            logger.error(f"Unexpected error in get_github_repository_branches: {e}")
            return {
                "success": False,
                "branches": [],
                "count": 0,
                "error": f"Tool execution error: {str(e)}",
                "error_code": "TOOL_ERROR",
                "message": "An unexpected error occurred while fetching repository branches",
                "summary": f"Tool error: {str(e)}",
            }

    @mcp.tool(
        name="get_github_repository_readme",
        description="Get README content from a GitHub repository.",
    )
    def get_github_repository_readme(owner: str, repo: str, branch: str = "main") -> dict:
        """
        Get README file content from a GitHub repository.

        Args:
            owner: Repository owner (user or organization)
            repo: Repository name
            branch: Branch name (default: main)

        Returns:
            dict: README content or error details
        """
        logger.info(
            f"get_github_repository_readme called with owner='{owner}', repo='{repo}', branch='{branch}'"
        )

        try:
            result = github_service.get_repository_readme(owner, repo, branch)

            if result.get("success"):
                readme_data = result.get("data", {})
                content = result.get("content", "")
                filename = result.get("filename", "README")

                # Create preview of content (first 500 chars)
                content_preview = content[:500] + "..." if len(content) > 500 else content

                # Count lines and words
                lines = len(content.split("\n")) if content else 0
                words = len(content.split()) if content else 0

                # Create summary
                summary_text = f"""README Content from {owner}/{repo}:{branch}
**File:** {filename}
**Size:** {readme_data.get('size', 0)} bytes
**Lines:** {lines}
**Words:** {words}

**Preview:**
```markdown
{content_preview}
```"""

                return {
                    "success": True,
                    "readme": {
                        "filename": filename,
                        "content": content,
                        "size": readme_data.get("size", 0),
                        "lines": lines,
                        "words": words,
                        "sha": readme_data.get("sha", ""),
                        "html_url": readme_data.get("html_url", ""),
                        "download_url": readme_data.get("download_url", ""),
                        "branch": branch,
                    },
                    "raw_data": readme_data,
                    "message": f"Successfully retrieved README from {owner}/{repo}:{branch}",
                    "summary": summary_text,
                }
            else:
                return {
                    "success": False,
                    "readme": None,
                    "error": result.get("error", "Unknown error occurred"),
                    "error_code": result.get("error_code", "UNKNOWN_ERROR"),
                    "attempted_files": result.get("attempted_files", []),
                    "message": f"Failed to retrieve README from {owner}/{repo}:{branch}",
                    "summary": f"Error: {result.get('error', 'Unknown error')}",
                }

        except Exception as e:
            logger.error(f"Unexpected error in get_github_repository_readme: {e}")
            return {
                "success": False,
                "readme": None,
                "error": f"Tool execution error: {str(e)}",
                "error_code": "TOOL_ERROR",
                "message": "An unexpected error occurred while fetching README",
                "summary": f"Tool error: {str(e)}",
            }

    @mcp.tool(
        name="get_github_repository_file",
        description="Get specific file content from a GitHub repository.",
    )
    def get_github_repository_file(
        owner: str, repo: str, file_path: str, branch: str = "main"
    ) -> dict:
        """
        Get specific file content from a GitHub repository.

        Args:
            owner: Repository owner (user or organization)
            repo: Repository name
            file_path: Path to the file (e.g., "docs/api.md", "src/main.py")
            branch: Branch name (default: main)

        Returns:
            dict: File content or error details
        """
        logger.info(
            f"get_github_repository_file called with owner='{owner}', repo='{repo}', file_path='{file_path}', branch='{branch}'"
        )

        try:
            result = github_service.get_repository_file_content(owner, repo, file_path, branch)

            if result.get("success"):
                file_data = result.get("data", {})
                content = result.get("content", "")
                filename = result.get("filename", file_path)

                # Create preview of content (first 500 chars)
                content_preview = content[:500] + "..." if len(content) > 500 else content

                # Count lines
                lines = len(content.split("\n")) if content else 0

                # Detect file type
                file_extension = filename.split(".")[-1].lower() if "." in filename else "unknown"

                # Create summary
                summary_text = f"""File Content from {owner}/{repo}:{branch}
**Path:** {file_path}
**File:** {filename}
**Type:** {file_extension}
**Size:** {file_data.get('size', 0)} bytes
**Lines:** {lines}

**Preview:**
```{file_extension}
{content_preview}
```"""

                return {
                    "success": True,
                    "file": {
                        "filename": filename,
                        "path": file_path,
                        "content": content,
                        "size": file_data.get("size", 0),
                        "lines": lines,
                        "extension": file_extension,
                        "sha": file_data.get("sha", ""),
                        "html_url": file_data.get("html_url", ""),
                        "download_url": file_data.get("download_url", ""),
                        "branch": branch,
                    },
                    "raw_data": file_data,
                    "message": f"Successfully retrieved file '{file_path}' from {owner}/{repo}:{branch}",
                    "summary": summary_text,
                }
            else:
                error_msg = result.get("error", "Unknown error occurred")
                if result.get("error_code") == "IS_DIRECTORY":
                    directory_contents = result.get("directory_contents", [])
                    return {
                        "success": False,
                        "file": None,
                        "error": error_msg,
                        "error_code": "IS_DIRECTORY",
                        "directory_contents": directory_contents,
                        "message": f"'{file_path}' is a directory containing {len(directory_contents)} items",
                        "summary": f"Directory contents: {', '.join(directory_contents[:5])}{'...' if len(directory_contents) > 5 else ''}",
                    }
                else:
                    return {
                        "success": False,
                        "file": None,
                        "error": error_msg,
                        "error_code": result.get("error_code", "UNKNOWN_ERROR"),
                        "message": f"Failed to retrieve file '{file_path}' from {owner}/{repo}:{branch}",
                        "summary": f"Error: {error_msg}",
                    }

        except Exception as e:
            logger.error(f"Unexpected error in get_github_repository_file: {e}")
            return {
                "success": False,
                "file": None,
                "error": f"Tool execution error: {str(e)}",
                "error_code": "TOOL_ERROR",
                "message": "An unexpected error occurred while fetching file",
                "summary": f"Tool error: {str(e)}",
            }

    @mcp.tool(
        name="get_github_user_info",
        description="Get authenticated user information from GitHub Enterprise.",
    )
    def get_github_user_info() -> dict:
        """
        Get information about the authenticated user.

        Returns:
            dict: User information or error details
        """
        logger.info("get_github_user_info called")

        try:
            result = github_service.get_user_info()

            if result.get("success"):
                user_data = result.get("data", {})

                # Format user information
                formatted_user = {
                    "login": user_data.get("login", "N/A"),
                    "name": user_data.get("name", "N/A"),
                    "email": user_data.get("email", "N/A"),
                    "company": user_data.get("company", "N/A"),
                    "location": user_data.get("location", "N/A"),
                    "bio": user_data.get("bio", "N/A"),
                    "public_repos": user_data.get("public_repos", 0),
                    "followers": user_data.get("followers", 0),
                    "following": user_data.get("following", 0),
                    "created_at": user_data.get("created_at", "N/A"),
                    "updated_at": user_data.get("updated_at", "N/A"),
                    "avatar_url": user_data.get("avatar_url", "N/A"),
                    "html_url": user_data.get("html_url", "N/A"),
                    "type": user_data.get("type", "User"),
                }

                # Create summary
                summary_text = f"""Authenticated User: {formatted_user['login']}
**Name:** {formatted_user['name']}
**Email:** {formatted_user['email']}
**Company:** {formatted_user['company']}
**Location:** {formatted_user['location']}
**Bio:** {formatted_user['bio']}
**Public Repos:** {formatted_user['public_repos']}
**Followers:** {formatted_user['followers']} | **Following:** {formatted_user['following']}
**Member Since:** {formatted_user['created_at']}
**Profile:** {formatted_user['html_url']}"""

                return {
                    "success": True,
                    "user": formatted_user,
                    "raw_data": user_data,
                    "message": "Successfully retrieved authenticated user information",
                    "summary": summary_text,
                }
            else:
                return {
                    "success": False,
                    "user": None,
                    "error": result.get("error", "Unknown error occurred"),
                    "error_code": result.get("error_code", "UNKNOWN_ERROR"),
                    "message": "Failed to retrieve authenticated user information",
                    "summary": f"Error: {result.get('error', 'Unknown error')}",
                }

        except Exception as e:
            logger.error(f"Unexpected error in get_github_user_info: {e}")
            return {
                "success": False,
                "user": None,
                "error": f"Tool execution error: {str(e)}",
                "error_code": "TOOL_ERROR",
                "message": "An unexpected error occurred while fetching user info",
                "summary": f"Tool error: {str(e)}",
            }

    @mcp.tool(
        name="get_github_latest_commit",
        description="Get the latest commit from a GitHub repository branch.",
    )
    def get_github_latest_commit(owner: str, repo: str, branch: str = "main") -> dict:
        """
        Get the latest commit from a GitHub repository branch.

        Args:
            owner: Repository owner (user or organization)
            repo: Repository name
            branch: Branch name (default: main)

        Returns:
            dict: Latest commit information or error details
        """
        logger.info(
            f"get_github_latest_commit called with owner='{owner}', repo='{repo}', branch='{branch}'"
        )

        try:
            result = github_service.get_latest_commit(owner, repo, branch)

            if result.get("success"):
                commit_data = result.get("data", {})

                # Create formatted summary
                summary_text = f"""Latest Commit from {owner}/{repo}:{branch}
    **SHA:** {commit_data.get('sha', 'N/A')[:8]}...
    **Author:** {commit_data.get('author', {}).get('name', 'Unknown')}
    **Date:** {commit_data.get('author', {}).get('date', 'Unknown')}
    **Message:** {commit_data.get('message', 'No message')[:100]}{'...' if len(commit_data.get('message', '')) > 100 else ''}

    **URL:** {commit_data.get('url', 'N/A')}"""

                return {
                    "success": True,
                    "commit": {
                        "sha": commit_data.get("sha", ""),
                        "short_sha": commit_data.get("sha", "")[:8],
                        "message": commit_data.get("message", ""),
                        "author": commit_data.get("author", {}),
                        "committer": commit_data.get("committer", {}),
                        "url": commit_data.get("url", ""),
                        "html_url": commit_data.get("url", ""),
                        "tree_sha": commit_data.get("tree_sha", ""),
                        "branch": branch,
                    },
                    "raw_data": commit_data,
                    "message": f"Successfully retrieved latest commit from {owner}/{repo}:{branch}",
                    "summary": summary_text,
                }
            else:
                return {
                    "success": False,
                    "commit": None,
                    "error": result.get("error", "Unknown error occurred"),
                    "error_code": result.get("error_code", "UNKNOWN_ERROR"),
                    "message": f"Failed to retrieve latest commit from {owner}/{repo}:{branch}",
                    "summary": f"Error: {result.get('error', 'Unknown error')}",
                }

        except Exception as e:
            logger.error(f"Unexpected error in get_github_latest_commit: {e}")
            return {
                "success": False,
                "commit": None,
                "error": f"Tool execution error: {str(e)}",
                "error_code": "TOOL_ERROR",
                "message": "An unexpected error occurred while fetching latest commit",
                "summary": f"Tool error: {str(e)}",
            }

    @mcp.tool(
        name="get_public_github_readme",
        description="Get README content from a public GitHub repository.",
    )
    def get_public_github_readme(owner: str, repo: str, branch: str = "main") -> dict:
        """
        Get README file content from a public GitHub repository (always uses api.github.com).

        Args:
            owner: Repository owner (user or organization)
            repo: Repository name
            branch: Branch name (default: main)

        Returns:
            dict: README content or error details
        """
        logger.info(
            f"get_public_github_readme called with owner='{owner}', repo='{repo}', branch='{branch}'"
        )

        try:
            result = github_service.get_public_github_readme(owner, repo, branch)

            if result.get("success"):
                readme_data = result.get("data", {})
                content = result.get("content", "")
                filename = result.get("filename", "README")

                # Create preview of content (first 500 chars)
                content_preview = content[:500] + "..." if len(content) > 500 else content

                # Count lines and words
                lines = len(content.split("\n")) if content else 0
                words = len(content.split()) if content else 0

                # Create summary
                summary_text = f"""README Content from Public GitHub {owner}/{repo}:{branch}
    **File:** {filename}
    **Size:** {readme_data.get('size', 0)} bytes
    **Lines:** {lines}
    **Words:** {words}

    **Preview:**
    ```markdown
    {content_preview}
    ```"""

                return {
                    "success": True,
                    "readme": {
                        "filename": filename,
                        "content": content,
                        "size": readme_data.get("size", 0),
                        "lines": lines,
                        "words": words,
                        "sha": readme_data.get("sha", ""),
                        "html_url": readme_data.get("html_url", ""),
                        "download_url": readme_data.get("download_url", ""),
                        "branch": branch,
                    },
                    "raw_data": readme_data,
                    "message": f"Successfully retrieved README from public GitHub: {owner}/{repo}:{branch}",
                    "summary": summary_text,
                }
            else:
                return {
                    "success": False,
                    "readme": None,
                    "error": result.get("error", "Unknown error occurred"),
                    "error_code": result.get("error_code", "UNKNOWN_ERROR"),
                    "message": f"Failed to retrieve README from public GitHub: {owner}/{repo}:{branch}",
                    "summary": f"Error: {result.get('error', 'Unknown error')}",
                }

        except Exception as e:
            logger.error(f"Unexpected error in get_public_github_readme: {e}")
            return {
                "success": False,
                "readme": None,
                "error": f"Tool execution error: {str(e)}",
                "error_code": "TOOL_ERROR",
                "message": "An unexpected error occurred while fetching README from public GitHub",
                "summary": f"Tool error: {str(e)}",
            }

    @mcp.tool(
        name="github_tool_server_status",
        description="Check if the MCP GitHub Tool server is online and get its version.",
    )
    def github_tool_server_status() -> dict:
        """
        Check if the GitHub tool server is running.

        Returns:
            dict: Server status information
        """
        return {
            "status": "online",
            "message": "MCP GitHub Tool server is running",
            "version": __version__,
            "tools": [
                "get_github_repository_info",
                "get_github_rate_limit",
                "get_github_repository_branches",
                "get_github_repository_readme",
                "get_public_github_readme",
                "get_github_repository_file",
                "get_github_user_info",
            ],
        }

    logger.debug("GitHub MCP tools registered")
