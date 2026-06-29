from __future__ import annotations
from dataclasses import dataclass, field, asdict


@dataclass
class RawResult:
    title: str
    url: str
    snippet: str


@dataclass
class CleanResult:
    title: str
    url: str
    snippet: str
    content: str
    score: float
    reasons: list[str] = field(default_factory=list)

    def to_public(self) -> dict:
        d = asdict(self)
        d.pop("reasons", None)
        return d
