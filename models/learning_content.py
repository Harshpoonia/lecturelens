"""
models/learning_content.py

Parsed AI-generated learning content.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Chapter:
    seconds: int
    title: str


@dataclass
class LearningContent:
    executive_summary: str
    key_points: str
    study_notes: str
    important_concepts: str
    chapters: list[Chapter] = field(default_factory=list)

    def as_dict(self) -> dict[str, str]:
        return {
            "Executive Summary": self.executive_summary,
            "Key Points": self.key_points,
            "Study Notes": self.study_notes,
            "Important Concepts": self.important_concepts,
        }
