from pydantic import BaseModel
from typing import Optional, Dict

class ChatRequest(BaseModel):
    prompt: str
    agent_name: Optional[str] = "general_agent"

    class Config:
        json_schema_extra  = {
            "example": {
                "prompt": "Get all files uploaded today.",
                "agent_name": "file_agent"
            }
        }

class ChatResponse(BaseModel):
    response: str
    token_usage: Optional[Dict[str, int]] = None
    agent_used: Optional[str] = None

    class Config:
        json_schema_extra  = {
            "example": {
                "response": "Here are the files uploaded today: ...",
                "token_usage": {
                    "total_tokens": 200,
                    "prompt_tokens": 80,
                    "completion_tokens": 120
                },
                "agent_used": "file_agent"
            }
        }