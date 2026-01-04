"""Pattern definitions and matching utilities."""

from __future__ import annotations

import re
import yaml
from typing import List, Optional, Pattern


class Pattern:
    def __init__(self, pattern_id: str, regex: str | None = None, keywords: List[str] | None = None, severity: float = 0.5):
        self.id = pattern_id
        self.regex = re.compile(regex, re.IGNORECASE) if regex else None
        self.keywords = [k.lower() for k in keywords] if keywords else []
        self.severity = severity

    def match(self, text: str) -> bool:
        if self.regex and self.regex.search(text):
            return True
        lower_text = text.lower()
        return any(k in lower_text for k in self.keywords)


DEFAULT_PATTERNS: List[Pattern] = [
    Pattern(
        "ignore_instructions",
        regex=r"(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|prompts?|rules?)",
        severity=0.9,
    ),
    Pattern(
        "role_manipulation",
        regex=r"(you\s+are\s+now|pretend\s+(to\s+be|you\s+are)|act\s+as|your\s+new\s+role)",
        severity=0.85,
    ),
    Pattern(
        "system_prompt_reference",
        regex=r"(system\s+prompt|end\s+of\s+(system|instructions)|<\|system\|>|\[INST\])",
        severity=0.8,
    ),
    Pattern(
        "jailbreak_keywords",
        keywords=["dan", "developer mode", "jailbreak", "no restrictions", "bypass", "unlock"],
        severity=0.95,
    ),
    Pattern(
        "encoded_base64",
        regex=r"(?:[A-Za-z0-9+/]{4}){10,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?",
        severity=0.7,
    ),
    # Typographic visual injection patterns
    Pattern(
        "output_manipulation",
        regex=r"(just\s+)?(output|respond|reply|answer|say)\s+['\"]?\w+['\"]?",
        severity=0.85,
    ),
    Pattern(
        "conditional_injection",
        regex=r"when\s+(asked|prompted|questioned)\s+(about|for|regarding)",
        severity=0.8,
    ),
    Pattern(
        "response_override",
        regex=r"(always|only|must)\s+(respond|output|say|reply)\s+(with|as)",
        severity=0.9,
    ),
    Pattern(
        "task_hijacking",
        keywords=["instead of", "rather than", "not the", "override", "replace with"],
        severity=0.75,
    ),
    Pattern(
        "sorry_injection",
        regex=r"(output|say|respond|reply)\s+['\"]?sorry['\"]?",
        severity=0.85,
    ),
]


def find_matches(text: str, patterns: Optional[List[Pattern]] = None) -> List[Pattern]:
    patterns = patterns or DEFAULT_PATTERNS
    return [p for p in patterns if p.match(text)]


def load_patterns(path: Optional[str]) -> List[Pattern]:
    if not path:
        return DEFAULT_PATTERNS
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        loaded: List[Pattern] = []
        for entry in data.get("patterns", []):
            loaded.append(
                Pattern(
                    pattern_id=entry.get("id"),
                    regex=entry.get("regex"),
                    keywords=entry.get("keywords"),
                    severity=entry.get("severity", 0.5),
                )
            )
        return loaded or DEFAULT_PATTERNS
    except Exception:
        return DEFAULT_PATTERNS
