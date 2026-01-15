from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class CommentAuthor:
    username: str
    profile_url: str = ''
    profile_picture_url: str = ''
    is_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'username': self.username,
            'profile_url': self.profile_url,
            'profile_picture_url': self.profile_picture_url,
            'is_verified': self.is_verified
        }

@dataclass
class Comment:
    id: str
    text: str
    author: CommentAuthor
    timestamp: str  # Original string e.g., "1w"
    timestamp_iso: str  # ISO 8601 string
    likes_count: int
    reply_count: int
    permalink: str  # URL to the comment
    replies: List['Comment'] = field(default_factory=list)
    is_reply: bool = False
    parent_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'text': self.text,
            'author': self.author.to_dict(),
            'timestamp': self.timestamp,
            'timestamp_iso': self.timestamp_iso,
            'likes_count': self.likes_count,
            'reply_count': self.reply_count,
            'permalink': self.permalink,
            'is_reply': self.is_reply,
            'parent_id': self.parent_id,
            'replies': [r.to_dict() for r in self.replies]
        }

@dataclass
class Collaborator:
    username: str
    profile_url: str = ''
    profile_picture_url: str = ''
    is_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'username': self.username,
            'profile_url': self.profile_url,
            'profile_picture_url': self.profile_picture_url,
            'is_verified': self.is_verified
        }

# Backward compatibility
CommentData = Comment
