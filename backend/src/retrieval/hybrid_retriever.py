"""
Hybrid retrieval:
  1. Load documents and split them into one chunk per '##' section
  2. BM25 (sparse) and MiniLM embeddings (dense)
  3. Reciprocal Rank Fusion of both rankings
  4. Drop near-duplicate chunks
  5. Cross-encoder reranking

Embeddings are cached in .cache/ and rebuilt automatically when the KB changes.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

from src import config

RRF_K = 60


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    language: str = "any"   # knowledge_base/<language>/...; files at the top level apply to all


@dataclass
class Passage:
    chunk: Chunk
    score: float  # cross-encoder logit, higher = more relevant

    @property
    def relevance(self) -> float:
        return 1 / (1 + math.exp(-self.score))


# ─────────────────────────────────────────────────────────────────────────────
# Loading & chunking
# ─────────────────────────────────────────────────────────────────────────────

def chunk_text(text: str, size: int = config.CHUNK_SIZE, overlap: int = config.CHUNK_OVERLAP) -> list[str]:
    """Pack whole paragraphs into ~`size`-word chunks; carry ~`overlap` words over."""
    pieces: list[str] = []
    for para in (p.strip() for p in re.split(r"\n\s*\n", text)):
        if not para:
            continue
        words = para.split()
        if len(words) <= size:
            pieces.append(para)
        else:  # very long paragraph: split by words
            step = size - overlap
            pieces += [" ".join(words[i:i + size]) for i in range(0, len(words), step)]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for piece in pieces:
        n = len(piece.split())
        if current and current_len + n > size:
            chunks.append("\n\n".join(current))
            carry, carried = [], 0
            for prev in reversed(current):
                m = len(prev.split())
                if carried + m > overlap:
                    break
                carry.insert(0, prev)
                carried += m
            if not carry:  # last paragraph longer than the overlap: carry its tail
                carry = [" ".join(current[-1].split()[-overlap:])]
                carried = len(carry[0].split())
            current, current_len = carry, carried
        current.append(piece)
        current_len += n
    if current:
        chunks.append("\n\n".join(current))
    return chunks


HEADING_RE = re.compile(r"^(#{1,2})\s+(.+)")   # '#' and '##' start a section; '###' stays inside


def split_sections(text: str) -> tuple[str | None, list[str]]:
    """Split markdown at '#'/'##' headings (ignoring '#' comments inside code fences).
    Returns (document title from the first '#' heading, list of sections)."""
    title: str | None = None
    sections: list[str] = []
    current: list[str] = []
    in_code = False

    def flush():
        lines = [l for l in current if l.strip()]
        if lines and not (len(lines) == 1 and HEADING_RE.match(lines[0])):   # skip bare headings
            sections.append("\n".join(current).strip())

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
        m = None if in_code else HEADING_RE.match(line)
        if m:
            flush()
            if m.group(1) == "#" and title is None:
                title, current = m.group(2).strip(), []
                continue
            current = [line]
        else:
            current.append(line)
    flush()
    return title, sections


def _read_file(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in (".md", ".txt", ".py", ".json"):
        return path.read_text(encoding="utf-8")
    if suffix in (".html", ".htm"):
        # Convert to markdown-ish text so HTML docs are split into sections the same way
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        for tag in soup(["head", "script", "style"]):
            tag.decompose()
        for pre in soup.find_all("pre"):
            pre.insert_before("\n```\n")
            pre.insert_after("\n```\n")
        for level in (1, 2, 3):
            for h in soup.find_all(f"h{level}"):
                h.insert_before("\n\n" + "#" * level + " ")
                h.insert_after("\n\n")
        for tag in soup.find_all(["p", "div", "ul", "ol", "table"]):
            tag.insert_after("\n\n")
        for tag in soup.find_all(["li", "tr", "br"]):
            tag.insert_after("\n")
        return soup.get_text()
    return None


def load_documents(kb_dir: Path = config.KB_DIR) -> list[Chunk]:
    """One chunk per '##' section (long sections are split further).
    The first subfolder is the language: knowledge_base/python/x.md -> "python"."""
    kb_dir = Path(kb_dir)
    if not kb_dir.is_dir():
        raise FileNotFoundError(f"Knowledge base folder not found: {kb_dir}")

    chunks: list[Chunk] = []
    for path in sorted(kb_dir.rglob("*")):
        if not path.is_file():
            continue
        text = _read_file(path)
        if not text or not text.strip():
            continue
        rel = path.relative_to(kb_dir)
        language = rel.parts[0].lower() if len(rel.parts) > 1 else "any"
        doc_id = rel.with_suffix("").as_posix()
        h1, sections = split_sections(text)
        title = h1 or path.stem.replace("_", " ").title()
        n = 0
        for section in sections:
            heading = section.splitlines()[0] if section.startswith("#") else ""
            for i, piece in enumerate(chunk_text(section)):
                if i > 0 and heading:
                    piece = f"{heading} (continued)\n\n{piece}"
                chunks.append(Chunk(chunk_id=f"{doc_id}::{n}", doc_id=doc_id, title=title, text=piece,
                                    language=language))
                n += 1
    if not chunks:
        raise ValueError(f"No .md/.txt/.html/.py/.json documents found in {kb_dir}")
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Retriever
# ─────────────────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


class HybridRetriever:
    def __init__(self, chunks: list[Chunk], cache_dir: Path = config.CACHE_DIR):
        self.chunks = chunks
        self.bm25 = BM25Okapi([_tokenize(f"{c.title}\n{c.text}") for c in chunks])
        self.embedder = SentenceTransformer(config.EMBED_MODEL)
        self.reranker = CrossEncoder(config.RERANK_MODEL, max_length=512)
        self.embeddings = self._embeddings(Path(cache_dir))

    @classmethod
    def from_folder(cls, kb_dir: Path = config.KB_DIR) -> "HybridRetriever":
        return cls(load_documents(kb_dir))

    def _embeddings(self, cache_dir: Path) -> np.ndarray:
        fingerprint = hashlib.sha256(
            (config.EMBED_MODEL + "".join(c.chunk_id + c.text for c in self.chunks)).encode()
        ).hexdigest()[:16]
        cache_file = cache_dir / f"embeddings_{fingerprint}.npy"
        if cache_file.exists():
            return np.load(cache_file)
        emb = self.embedder.encode(
            [c.text for c in self.chunks], batch_size=64, normalize_embeddings=True, show_progress_bar=True
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        np.save(cache_file, emb)
        return emb

    @property
    def languages(self) -> list[str]:
        return sorted({c.language for c in self.chunks} - {"any"})

    def search(self, query: str, top_k: int = config.TOP_K, language: str | None = None) -> list[Passage]:
        """Search all chunks, or only chunks for `language` (plus language-neutral ones)."""
        n = config.CANDIDATES
        allowed = np.array([language is None or c.language in (language, "any") for c in self.chunks])

        # 1-2. Sparse + dense rankings (lists of chunk indices), restricted to the language
        bm25_scores = np.where(allowed, self.bm25.get_scores(_tokenize(query)), -np.inf)
        bm25_rank = [int(i) for i in np.argsort(bm25_scores)[::-1][:n] if bm25_scores[i] > 0]
        q_emb = self.embedder.encode([query], normalize_embeddings=True)
        dense_scores = np.where(allowed, (self.embeddings @ q_emb.T).ravel(), -np.inf)
        dense_rank = [int(i) for i in np.argsort(dense_scores)[::-1][:n] if allowed[i]]

        # 3. Reciprocal Rank Fusion
        fused: dict[int, float] = {}
        for ranking in (bm25_rank, dense_rank):
            for rank, idx in enumerate(ranking, start=1):
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (RRF_K + rank)
        candidates = sorted(fused, key=fused.get, reverse=True)[:n]

        # 4. Near-duplicate removal (keeps the higher-ranked copy). Embeddings cover the
        #    section text only, so copies of a section in two documents still match.
        kept: list[int] = []
        for idx in candidates:
            if all(float(self.embeddings[idx] @ self.embeddings[k]) <= config.DEDUP_THRESHOLD for k in kept):
                kept.append(idx)
        if not kept:
            return []

        # 5. Cross-encoder rerank
        scores = self.reranker.predict([(query, f"{self.chunks[i].title}\n{self.chunks[i].text}") for i in kept])
        passages = [Passage(self.chunks[i], float(s)) for i, s in zip(kept, scores)]
        passages.sort(key=lambda p: p.score, reverse=True)
        return passages[:top_k]
