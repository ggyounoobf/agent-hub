"""
GitHub service for GitHub API interactions.

This module handles all GitHub-related API calls and business logic,
separating concerns from the MCP tool definitions.
"""

from typing import Dict, Optional

import httpx

from config import GITHUB_API_BASE_URL, GITHUB_API_TIMEOUT, GITHUB_PAT, GITHUB_SSL_VERIFY

from ..utils.logging import logger


class GitHubService:
    """Service class for GitHub API operations."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        token: Optional[str] = None,
    ):
        """
        Initialize the GitHubService.

        Args:
            base_url: Override the base URL from config
            timeout: Override the timeout from config
            token: Override the PAT from config
        """
        self.base_url = base_url or GITHUB_API_BASE_URL
        self.timeout = timeout or GITHUB_API_TIMEOUT
        self.token = token or GITHUB_PAT
        self.ssl_verify = GITHUB_SSL_VERIFY

        if not self.token:
            logger.warning(
                "No GitHub PAT found. Some operations may fail due to rate limiting or private repo access."
            )

    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for GitHub API requests.

        Returns:
            dict: Headers including authentication if token is available
        """
        headers = {"Accept": "application/vnd.github.v3+json"}

        if self.token:
            headers["Authorization"] = f"token {self.token}"

        return headers

    def get_repository_info(self, owner: str, repo: str) -> Dict:
        """
        Get repository information from GitHub API.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            dict: API response containing repository info or error information
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}"
            headers = self._get_headers()

            logger.info(f"Making GET request to {url}")

            with httpx.Client(timeout=self.timeout, verify=self.ssl_verify) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()
                logger.info(f"Successfully retrieved repository info for {owner}/{repo}")

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": data,
                    "message": f"Successfully retrieved repository info for {owner}/{repo}",
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                error_msg = "Authentication failed. Please check your GitHub PAT."
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "AUTHENTICATION_ERROR",
                    "status_code": 401,
                }
            elif e.response.status_code == 403:
                error_msg = "Access forbidden. Check your PAT permissions or rate limits."
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "FORBIDDEN_ERROR",
                    "status_code": 403,
                }
            elif e.response.status_code == 404:
                error_msg = f"Repository '{owner}/{repo}' not found or you don't have access"
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "NOT_FOUND",
                    "status_code": 404,
                }
            else:
                error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "HTTP_ERROR",
                    "status_code": e.response.status_code,
                }

        except httpx.ConnectError:
            error_msg = f"Connection failed to {self.base_url}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "error_code": "CONNECTION_ERROR"}

        except httpx.TimeoutException:
            error_msg = f"Request timed out after {self.timeout} seconds"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "error_code": "TIMEOUT_ERROR"}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "error_code": "UNKNOWN_ERROR"}

    def get_rate_limit(self) -> Dict:
        """
        Get GitHub API rate limit information.

        Returns:
            dict: API response containing rate limit info or error information
        """
        try:
            url = f"{self.base_url}/rate_limit"
            headers = self._get_headers()

            logger.info(f"Making GET request to {url}")

            with httpx.Client(timeout=self.timeout, verify=self.ssl_verify) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()
                logger.info("Successfully retrieved rate limit information")

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": data,
                    "message": "Successfully retrieved rate limit information",
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                error_msg = "Authentication failed. Please check your GitHub PAT."
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "AUTHENTICATION_ERROR",
                    "status_code": 401,
                }
            else:
                error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "HTTP_ERROR",
                    "status_code": e.response.status_code,
                }

        except Exception as e:
            error_msg = f"Error fetching rate limit: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "error_code": "API_ERROR"}

    def get_repository_branches(self, owner: str, repo: str) -> Dict:
        """
        Get repository branches from GitHub API.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            dict: API response containing repository branches or error information
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/branches"
            headers = self._get_headers()

            logger.info(f"Making GET request to {url}")

            with httpx.Client(timeout=self.timeout, verify=self.ssl_verify) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()
                count = len(data) if isinstance(data, list) else 0
                logger.info(f"Successfully retrieved {count} branches for {owner}/{repo}")

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": data,
                    "count": count,
                    "message": f"Successfully retrieved {count} branches for {owner}/{repo}",
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                error_msg = "Authentication failed. Please check your GitHub PAT."
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "AUTHENTICATION_ERROR",
                    "status_code": 401,
                }
            elif e.response.status_code == 403:
                error_msg = "Access forbidden. Check your PAT permissions."
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "FORBIDDEN_ERROR",
                    "status_code": 403,
                }
            elif e.response.status_code == 404:
                error_msg = f"Repository '{owner}/{repo}' not found or you don't have access"
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "NOT_FOUND",
                    "status_code": 404,
                }
            else:
                error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "HTTP_ERROR",
                    "status_code": e.response.status_code,
                }

        except Exception as e:
            error_msg = f"Error fetching branches for {owner}/{repo}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "error_code": "API_ERROR"}

    def get_user_info(self) -> Dict:
        """
        Get authenticated user information.

        Returns:
            dict: API response containing user info or error information
        """
        try:
            url = f"{self.base_url}/user"
            headers = self._get_headers()

            logger.info(f"Making GET request to {url}")

            with httpx.Client(timeout=self.timeout, verify=self.ssl_verify) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()
                logger.info("Successfully retrieved authenticated user information")

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": data,
                    "message": "Successfully retrieved authenticated user information",
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                error_msg = "Authentication failed. Please check your GitHub PAT."
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "AUTHENTICATION_ERROR",
                    "status_code": 401,
                }
            else:
                error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "HTTP_ERROR",
                    "status_code": e.response.status_code,
                }

        except Exception as e:
            error_msg = f"Error fetching user info: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "error_code": "API_ERROR"}

    def get_repository_commits(
        self, owner: str, repo: str, branch: str = "main", per_page: int = 30
    ) -> Dict:
        """
        Get repository commits from GitHub API.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name (default: main)
            per_page: Number of commits to retrieve (default: 30)

        Returns:
            dict: API response containing repository commits or error information
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/commits"
            headers = self._get_headers()
            params = {"sha": branch, "per_page": per_page}

            logger.info(f"Making GET request to {url} for branch '{branch}'")

            with httpx.Client(timeout=self.timeout, verify=self.ssl_verify) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()

                data = response.json()
                count = len(data) if isinstance(data, list) else 0
                logger.info(f"Successfully retrieved {count} commits for {owner}/{repo}:{branch}")

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": data,
                    "count": count,
                    "branch": branch,
                    "message": f"Successfully retrieved {count} commits for {owner}/{repo}:{branch}",
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                error_msg = "Authentication failed. Please check your GitHub PAT."
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "AUTHENTICATION_ERROR",
                    "status_code": 401,
                }
            elif e.response.status_code == 404:
                error_msg = f"Repository '{owner}/{repo}' or branch '{branch}' not found"
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "NOT_FOUND",
                    "status_code": 404,
                }
            else:
                error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "HTTP_ERROR",
                    "status_code": e.response.status_code,
                }

        except Exception as e:
            error_msg = f"Error fetching commits for {owner}/{repo}:{branch}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "error_code": "API_ERROR"}

    def get_latest_commit(self, owner: str, repo: str, branch: str = "main") -> Dict:
        """
        Get the latest commit from a repository branch.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name (default: main)

        Returns:
            dict: API response containing latest commit info or error information
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/commits"
            headers = self._get_headers()
            # Only get the latest commit
            params = {"sha": branch, "per_page": 1}

            logger.info(f"Getting latest commit from {url} for branch '{branch}'")

            with httpx.Client(timeout=self.timeout, verify=self.ssl_verify) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()

                data = response.json()

                if not data or len(data) == 0:
                    error_msg = (
                        f"No commits found in repository '{owner}/{repo}' on branch '{branch}'"
                    )
                    logger.warning(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "error_code": "NO_COMMITS_FOUND",
                        "status_code": 404,
                    }

                latest_commit = data[0]  # First commit is the latest
                commit_info = latest_commit.get("commit", {})
                author_info = commit_info.get("author", {})
                committer_info = commit_info.get("committer", {})

                logger.info(f"Successfully retrieved latest commit for {owner}/{repo}:{branch}")

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": {
                        "sha": latest_commit.get("sha", ""),
                        "message": commit_info.get("message", ""),
                        "author": {
                            "name": author_info.get("name", ""),
                            "email": author_info.get("email", ""),
                            "date": author_info.get("date", ""),
                        },
                        "committer": {
                            "name": committer_info.get("name", ""),
                            "email": committer_info.get("email", ""),
                            "date": committer_info.get("date", ""),
                        },
                        "url": latest_commit.get("html_url", ""),
                        "api_url": latest_commit.get("url", ""),
                        "tree_sha": commit_info.get("tree", {}).get("sha", ""),
                        "branch": branch,
                    },
                    "raw_data": latest_commit,
                    "message": f"Successfully retrieved latest commit for {owner}/{repo}:{branch}",
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                error_msg = "Authentication failed. Please check your GitHub PAT."
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "AUTHENTICATION_ERROR",
                    "status_code": 401,
                }
            elif e.response.status_code == 404:
                error_msg = f"Repository '{owner}/{repo}' or branch '{branch}' not found"
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "NOT_FOUND",
                    "status_code": 404,
                }
            else:
                error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "HTTP_ERROR",
                    "status_code": e.response.status_code,
                }

        except Exception as e:
            error_msg = f"Error fetching latest commit for {owner}/{repo}:{branch}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "error_code": "API_ERROR"}

    def search_repositories(
        self, query: str, sort: str = "updated", order: str = "desc", per_page: int = 30
    ) -> Dict:
        """
        Search repositories using GitHub API.

        Args:
            query: Search query
            sort: Sort field (stars, forks, help-wanted-issues, updated)
            order: Sort order (asc, desc)
            per_page: Number of results per page (max 100)

        Returns:
            dict: API response containing search results or error information
        """
        try:
            url = f"{self.base_url}/search/repositories"
            headers = self._get_headers()
            params = {
                "q": query,
                "sort": sort,
                "order": order,
                "per_page": min(per_page, 100),  # GitHub API max is 100
            }

            logger.info(f"Making GET request to {url} with query: '{query}'")

            with httpx.Client(timeout=self.timeout, verify=self.ssl_verify) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()

                data = response.json()
                total_count = data.get("total_count", 0)
                items = data.get("items", [])
                logger.info(f"Successfully found {total_count} repositories matching '{query}'")

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": data,
                    "total_count": total_count,
                    "items": items,
                    "query": query,
                    "message": f"Successfully found {total_count} repositories matching '{query}'",
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                error_msg = "Authentication failed. Please check your GitHub PAT."
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "AUTHENTICATION_ERROR",
                    "status_code": 401,
                }
            elif e.response.status_code == 403:
                error_msg = "Rate limit exceeded or search forbidden."
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "RATE_LIMIT_ERROR",
                    "status_code": 403,
                }
            else:
                error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "HTTP_ERROR",
                    "status_code": e.response.status_code,
                }

        except Exception as e:
            error_msg = f"Error searching repositories with query '{query}': {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "error_code": "API_ERROR"}

    def get_repository_issues(
        self, owner: str, repo: str, state: str = "open", per_page: int = 30
    ) -> Dict:
        """
        Get repository issues from GitHub API.

        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state (open, closed, all)
            per_page: Number of issues to retrieve (default: 30)

        Returns:
            dict: API response containing repository issues or error information
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/issues"
            headers = self._get_headers()
            params = {"state": state, "per_page": per_page}

            logger.info(f"Making GET request to {url} for {state} issues")

            with httpx.Client(timeout=self.timeout, verify=self.ssl_verify) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()

                data = response.json()
                count = len(data) if isinstance(data, list) else 0
                logger.info(f"Successfully retrieved {count} {state} issues for {owner}/{repo}")

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": data,
                    "count": count,
                    "state": state,
                    "message": f"Successfully retrieved {count} {state} issues for {owner}/{repo}",
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                error_msg = "Authentication failed. Please check your GitHub PAT."
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "AUTHENTICATION_ERROR",
                    "status_code": 401,
                }
            elif e.response.status_code == 404:
                error_msg = f"Repository '{owner}/{repo}' not found or you don't have access"
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "NOT_FOUND",
                    "status_code": 404,
                }
            else:
                error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "HTTP_ERROR",
                    "status_code": e.response.status_code,
                }

        except Exception as e:
            error_msg = f"Error fetching issues for {owner}/{repo}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "error_code": "API_ERROR"}

    def get_repository_readme(self, owner: str, repo: str, branch: str = "main") -> Dict:
        """
        Get repository README content from GitHub API.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name (default: main)

        Returns:
            dict: API response containing README content or error information
        """
        try:
            # Try common README file names
            readme_files = [
                "README.md",
                "README.MD",
                "readme.md",
                "README.rst",
                "README.txt",
                "README",
            ]

            for readme_file in readme_files:
                url = f"{self.base_url}/repos/{owner}/{repo}/contents/{readme_file}"
                headers = self._get_headers()
                params = {"ref": branch}

                logger.info(f"Attempting to get {readme_file} from {url}")

                with httpx.Client(timeout=self.timeout, verify=self.ssl_verify) as client:
                    response = client.get(url, headers=headers, params=params)

                    if response.status_code == 200:
                        data = response.json()

                        # Decode base64 content
                        import base64

                        if data.get("encoding") == "base64":
                            content = base64.b64decode(data.get("content", "")).decode("utf-8")
                        else:
                            content = data.get("content", "")

                        logger.info(f"Successfully retrieved README from {owner}/{repo}:{branch}")

                        return {
                            "success": True,
                            "status_code": response.status_code,
                            "data": {
                                "filename": readme_file,
                                "content": content,
                                "size": data.get("size", 0),
                                "sha": data.get("sha", ""),
                                "download_url": data.get("download_url", ""),
                                "html_url": data.get("html_url", ""),
                                "encoding": data.get("encoding", ""),
                                "branch": branch,
                            },
                            "content": content,
                            "filename": readme_file,
                            "message": f"Successfully retrieved README from {owner}/{repo}:{branch}",
                        }
                    elif response.status_code == 404:
                        continue  # Try next README filename
                    else:
                        response.raise_for_status()

            # If we get here, no README was found
            error_msg = f"No README file found in repository '{owner}/{repo}' on branch '{branch}'"
            logger.warning(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "error_code": "README_NOT_FOUND",
                "status_code": 404,
                "attempted_files": readme_files,
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                error_msg = "Authentication failed. Please check your GitHub PAT."
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "AUTHENTICATION_ERROR",
                    "status_code": 401,
                }
            elif e.response.status_code == 403:
                error_msg = "Access forbidden. Check your PAT permissions."
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "FORBIDDEN_ERROR",
                    "status_code": 403,
                }
            elif e.response.status_code == 404:
                error_msg = f"Repository '{owner}/{repo}' or branch '{branch}' not found"
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "NOT_FOUND",
                    "status_code": 404,
                }
            else:
                error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "HTTP_ERROR",
                    "status_code": e.response.status_code,
                }

        except Exception as e:
            error_msg = f"Error fetching README for {owner}/{repo}:{branch}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "error_code": "API_ERROR"}

    def get_repository_file_content(
        self, owner: str, repo: str, file_path: str, branch: str = "main"
    ) -> Dict:
        """
        Get specific file content from GitHub repository.

        Args:
            owner: Repository owner
            repo: Repository name
            file_path: Path to the file (e.g., "docs/api.md", "src/main.py")
            branch: Branch name (default: main)

        Returns:
            dict: API response containing file content or error information
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{file_path}"
            headers = self._get_headers()
            params = {"ref": branch}

            logger.info(f"Making GET request to {url} for file '{file_path}'")

            with httpx.Client(timeout=self.timeout, verify=self.ssl_verify) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()

                data = response.json()

                # Handle directory vs file
                if isinstance(data, list):
                    return {
                        "success": False,
                        "error": f"'{file_path}' is a directory, not a file",
                        "error_code": "IS_DIRECTORY",
                        "directory_contents": [item.get("name", "") for item in data],
                    }

                # Decode file content
                import base64

                if data.get("encoding") == "base64":
                    content = base64.b64decode(data.get("content", "")).decode("utf-8")
                else:
                    content = data.get("content", "")

                logger.info(
                    f"Successfully retrieved file '{file_path}' from {owner}/{repo}:{branch}"
                )

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": {
                        "filename": data.get("name", file_path),
                        "path": file_path,
                        "content": content,
                        "size": data.get("size", 0),
                        "sha": data.get("sha", ""),
                        "download_url": data.get("download_url", ""),
                        "html_url": data.get("html_url", ""),
                        "encoding": data.get("encoding", ""),
                        "branch": branch,
                    },
                    "content": content,
                    "filename": data.get("name", file_path),
                    "message": f"Successfully retrieved file '{file_path}' from {owner}/{repo}:{branch}",
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                error_msg = f"File '{file_path}' not found in repository '{owner}/{repo}' on branch '{branch}'"
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "FILE_NOT_FOUND",
                    "status_code": 404,
                }
            else:
                error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "HTTP_ERROR",
                    "status_code": e.response.status_code,
                }

        except Exception as e:
            error_msg = f"Error fetching file '{file_path}' from {owner}/{repo}:{branch}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "error_code": "API_ERROR"}

    def get_public_github_readme(self, owner: str, repo: str, branch: str = "main") -> Dict:
        """
        Get repository README from public GitHub (always uses api.github.com).

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name (default: main)

        Returns:
            dict: API response containing README content or error information
        """
        try:
            # Always use public GitHub API
            url = f"https://api.github.com/repos/{owner}/{repo}/readme"

            # Create headers without token for public access, or with token for
            # higher rate limits
            headers = {"Accept": "application/vnd.github.v3+json"}
            # if self.token:
            #     headers["Authorization"] = f"token {self.token}"

            params = {"ref": branch}

            logger.info(f"Getting README from public GitHub: {url}")

            with httpx.Client(
                timeout=self.timeout, verify=True
            ) as client:  # Always verify SSL for public GitHub
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()

                data = response.json()

                # Decode base64 content
                import base64

                if data.get("encoding") == "base64":
                    content = base64.b64decode(data.get("content", "")).decode("utf-8")
                else:
                    content = data.get("content", "")

                logger.info(
                    f"Successfully retrieved README from public GitHub: {owner}/{repo}:{branch}"
                )

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": {
                        "filename": data.get("name"),
                        "content": content,
                        "size": data.get("size", 0),
                        "sha": data.get("sha", ""),
                        "download_url": data.get("download_url", ""),
                        "html_url": data.get("html_url", ""),
                        "encoding": data.get("encoding", ""),
                        "branch": branch,
                    },
                    "content": content,
                    "filename": data.get("name"),
                    "message": f"Successfully retrieved README from public GitHub: {owner}/{repo}:{branch}",
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                error_msg = f"Repository '{owner}/{repo}' or README not found on public GitHub"
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "README_NOT_FOUND",
                    "status_code": 404,
                }
            elif e.response.status_code == 403:
                error_msg = "Rate limit exceeded on public GitHub API"
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "status_code": 403,
                }
            else:
                error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "HTTP_ERROR",
                    "status_code": e.response.status_code,
                }

        except Exception as e:
            error_msg = (
                f"Error fetching README from public GitHub for {owner}/{repo}:{branch}: {str(e)}"
            )
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "error_code": "API_ERROR"}
