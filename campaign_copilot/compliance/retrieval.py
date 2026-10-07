"""Tiny retrieval index over the policy folder.

RAG without a vector database: the policy files are split into numbered paragraphs, each
paragraph is tokenised, and queries are scored with BM25. Standard library only, so it runs
offline and deterministically. Five short policy files do not need embeddings; the point is that
every compliance flag cites the exact paragraph that justifies it.
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

TOKEN = re.compile(r"[a-z0-9%$]+")
STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "for",
    "is",
    "are",
    "be",
    "may",
    "must",
    "that",
    "this",
    "with",
    "as",
    "at",
    "by",
    "it",
    "any",
    "not",
    "no",
}


def default_policy_dir() -> Path:
    return Path(os.environ.get("POLICY_DIR", "policies"))


@dataclass(frozen=True)
class Passage:
    policy_id: str  # e.g. "2.2"
    source: str  # file name
    title: str  # policy title line
    text: str

    @property
    def citation(self) -> str:
        return f"Policy {self.policy_id} ({self.source})"


def _tokens(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOP]


def load_passages(policy_dir: str | Path | None = None) -> list[Passage]:
    """Split each policy file into its numbered paragraphs (1.1, 1.2, ...)."""
    folder = Path(policy_dir) if policy_dir else default_policy_dir()
    passages: list[Passage] = []
    for path in sorted(folder.glob("*.txt")):
        lines = path.read_text(encoding="utf-8").splitlines()
        title = next(
            (ln.strip() for ln in lines[1:4] if ln.strip() and "POLICY" not in ln), path.stem
        )
        body = "\n".join(lines)
        for match in re.finditer(r"(?ms)^(\d+\.\d+)\s+(.*?)(?=^\d+\.\d+\s|\Z)", body):
            text = " ".join(match.group(2).split())
            passages.append(Passage(match.group(1), path.name, title, text))
    if not passages:
        raise FileNotFoundError(f"no policy paragraphs found in {folder.resolve()}")
    return passages


class PolicyIndex:
    """BM25 over policy paragraphs."""

    def __init__(self, passages: list[Passage], k1: float = 1.5, b: float = 0.75) -> None:
        self.passages = passages
        self.k1, self.b = k1, b
        self._docs = [_tokens(p.text) for p in passages]
        self._avg_len = sum(len(d) for d in self._docs) / len(self._docs)
        df: Counter[str] = Counter()
        for doc in self._docs:
            df.update(set(doc))
        n = len(self._docs)
        self._idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    @classmethod
    def from_dir(cls, policy_dir: str | Path | None = None) -> PolicyIndex:
        return cls(load_passages(policy_dir))

    def _score(self, query: list[str], doc: list[str]) -> float:
        tf = Counter(doc)
        score = 0.0
        for term in query:
            if term not in tf:
                continue
            f = tf[term]
            denom = f + self.k1 * (1 - self.b + self.b * len(doc) / self._avg_len)
            score += self._idf.get(term, 0.0) * f * (self.k1 + 1) / denom
        return score

    def search(self, query: str, k: int = 3) -> list[tuple[Passage, float]]:
        q = _tokens(query)
        scored = [(p, self._score(q, d)) for p, d in zip(self.passages, self._docs, strict=True)]
        scored = [s for s in scored if s[1] > 0]
        scored.sort(key=lambda s: (-s[1], s[0].policy_id))
        return scored[:k]

    def get(self, policy_id: str) -> Passage:
        for p in self.passages:
            if p.policy_id == policy_id:
                return p
        raise KeyError(policy_id)
