"""
utils/text_statistics.py

Transcript analytics: word/character counts, reading time, speaking
pace and most frequent terms.
"""

from __future__ import annotations

import math
import re
from collections import Counter

READING_WPM = 200

_STOPWORDS = set(
    """
    a about above after again against all also am an and any are aren't as at be because been
    before being below between both but by can can't cannot could couldn't did didn't do does
    doesn't doing don't down during each few for from further get gets getting go going gonna got
    had hadn't has hasn't have haven't having he he'd he'll he's her here here's hers herself him
    himself his how how's i i'd i'll i'm i've if in into is isn't it it's its itself just know
    let's like lot me more most mustn't my myself no nor not now of off ok okay on once one only
    or other ought our ours ourselves out over own really right said same say says see shan't she
    she'd she'll she's should shouldn't so some something such than that that's the their theirs
    them themselves then there there's these they they'd they'll they're they've thing things think
    this those through to too um uh under until up us very want was wasn't way we we'd we'll we're
    we've well were weren't what what's when when's where where's which while who who's whom why
    why's will with won't would wouldn't yeah yes you you'd you'll you're you've your yours yourself
    yourselves actually basically going kind sort mean little bit make made take two first new
    """.split()
)

_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")


def word_count(text: str) -> int:
    return len(text.split())


def character_count(text: str) -> int:
    return len(text)


def reading_time(text: str) -> int:
    """Estimated reading time in minutes at ~200 words/minute (min 1)."""
    words = word_count(text)
    return max(1, math.ceil(words / READING_WPM)) if words else 0


def speaking_pace(words: int, duration_seconds: float | None) -> int | None:
    """Words per minute spoken in the video, if the duration is known."""
    if not duration_seconds or duration_seconds < 1:
        return None
    return round(words / (duration_seconds / 60))


def top_terms(text: str, limit: int = 12) -> list[tuple[str, int]]:
    """Most frequent meaningful words (Latin-script languages only)."""
    words = [w.lower().strip("'-") for w in _WORD.findall(text or "")]
    counts = Counter(w for w in words if w not in _STOPWORDS and len(w) > 2)
    return counts.most_common(limit)
