"""
models/chat.py

A single message in a "chat with the video" conversation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class ChatMessage:
    role: Literal["user", "assistant"]
    content: str
    mode: str = "ask"
