"""
modules/youtube.py

Lightweight video metadata (title, channel, thumbnail) via YouTube's
public oEmbed endpoint — no API key required. Failures are non-fatal.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

OEMBED_URL = "https://www.youtube.com/oembed"


@dataclass(frozen=True)
class VideoMetadata:
    title: str | None = None
    channel: str | None = None
    thumbnail_url: str | None = None


def fetch_video_metadata(video_id: str, timeout: float = 5.0) -> VideoMetadata:
    try:
        response = requests.get(
            OEMBED_URL,
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=timeout,
        )
        if response.status_code != 200:
            return VideoMetadata()
        data = response.json()
        return VideoMetadata(
            title=data.get("title"),
            channel=data.get("author_name"),
            thumbnail_url=data.get("thumbnail_url"),
        )
    except (requests.RequestException, ValueError):
        return VideoMetadata()
