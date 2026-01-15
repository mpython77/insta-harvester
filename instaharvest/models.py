from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any

class CommentAuthor(BaseModel):
    username: str
    profile_url: str = Field(default='')
    profile_picture_url: str = Field(default='')
    is_verified: bool = Field(default=False)

class Comment(BaseModel):
    id: str
    text: str = Field(default="")
    author: CommentAuthor
    timestamp: str  # Original string e.g., "1w"
    timestamp_iso: str  # ISO 8601 string
    likes_count: int = Field(default=0, ge=0)
    reply_count: int = Field(default=0, ge=0)
    permalink: str = Field(default="")
    replies: List['Comment'] = Field(default_factory=list)
    is_reply: bool = Field(default=False)
    parent_id: Optional[str] = None
    
    @field_validator('likes_count', 'reply_count', mode='before')
    @classmethod
    def validate_counts(cls, v):
        """Handle '1,234' string format or simple parse errors"""
        if isinstance(v, str):
            try:
                return int(v.replace(',', '').replace('.', ''))
            except ValueError:
                return 0
        return v

class Collaborator(BaseModel):
    username: str
    profile_url: str = Field(default='')
    profile_picture_url: str = Field(default='')
    is_verified: bool = Field(default=False)

# Backward compatibility aliases
CommentData = Comment

