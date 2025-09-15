import httpx
from typing import Dict, Optional
from fastapi import HTTPException, status
from app.config.settings import GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_REDIRECT_URI


class GitHubOAuth:
    def __init__(self):
        self.client_id = GITHUB_CLIENT_ID
        self.client_secret = GITHUB_CLIENT_SECRET
        self.redirect_uri = GITHUB_REDIRECT_URI
        
        if not all([self.client_id, self.client_secret]):
            raise ValueError("GitHub OAuth credentials not configured properly")

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate GitHub OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "user:email repo",  # Request user info and repo access
            "state": state or "",
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://github.com/login/oauth/authorize?{query_string}"

    async def exchange_code_for_token(self, code: str) -> Dict:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange code for token"
                )
            
            return response.json()

    async def get_user_info(self, access_token: str) -> Dict:
        """Get user information from GitHub."""
        async with httpx.AsyncClient() as client:
            # Get user basic info
            user_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {access_token}"}
            )
            
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user information"
                )
            
            user_data = user_response.json()
            
            # Get user email (might be private)
            email_response = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"token {access_token}"}
            )
            
            primary_email = user_data.get("email")
            if not primary_email and email_response.status_code == 200:
                emails = email_response.json()
                primary_email_obj = next(
                    (email for email in emails if email.get("primary")), 
                    emails[0] if emails else None
                )
                if primary_email_obj:
                    primary_email = primary_email_obj["email"]
            
            return {
                "github_id": str(user_data["id"]),
                "username": user_data["login"],
                "email": primary_email,
                "full_name": user_data.get("name"),
                "avatar_url": user_data.get("avatar_url"),
            }
