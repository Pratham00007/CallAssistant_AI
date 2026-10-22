"""Knowledge Base Loader and Chunker for ZentroMart Capstone.
Parses all 21 Markdown files, tracks metadata and section IDs, and provides precedence weighting.
"""
import re
from pathlib import Path
from typing import Dict, List, Any
from .config import KB_DIR

PRECEDENCE_MAP = {
    ("policy", "current"): 1,
    ("agent_guide", "current"): 2,
    ("help", "current"): 3,
    ("faq", "current"): 4,
    ("marketing", "current"): 5,
    ("policy", "superseded"): 6,
    ("meta", "current"): 7,
}

class KBChunk:
    def __init__(self, sec_id: str, title: str, body: str, doc_meta: Dict[str, Any], file_name: str):
        self.sec_id = sec_id
        self.title = title
        self.body = body.strip()
        self.file_name = file_name
        self.doc_id = doc_meta.get("doc_id", "")
        self.doc_type = doc_meta.get("doc_type", "")
        self.effective_from = doc_meta.get("effective_from", "")
        self.status = doc_meta.get("status", "current")
        self.language = doc_meta.get("language", "en")
        self.supersedes = doc_meta.get("supersedes", "")
        self.superseded_by = doc_meta.get("superseded_by", "")
        self.rank = PRECEDENCE_MAP.get((self.doc_type, self.status), 10)
        self.full_content = f"[{self.sec_id}] {self.title}\n{self.body}"

    def to_dict(self):
        return {
            "sec_id": self.sec_id,
            "title": self.title,
            "body": self.body,
            "doc_id": self.doc_id,
            "doc_type": self.doc_type,
            "effective_from": self.effective_from,
            "status": self.status,
            "rank": self.rank,
            "language": self.language,
        }

    def __repr__(self):
        return f"<KBChunk {self.sec_id}: {self.title} (rank {self.rank})>"


class KnowledgeBase:
    def __init__(self, kb_dir: Path = KB_DIR):
        self.kb_dir = Path(kb_dir)
        self.chunks_by_id: Dict[str, KBChunk] = {}
        self.chunks: List[KBChunk] = []
        self._load_all()

    def _load_all(self):
        for md_file in sorted(self.kb_dir.glob("*.md")):
            self._parse_file(md_file)

    def _parse_file(self, file_path: Path):
        text = file_path.read_text(encoding="utf-8")
        doc_meta = {}
        
        # Parse YAML frontmatter
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        doc_meta[k.strip()] = v.strip()
                content = parts[2]
            else:
                content = text
        else:
            content = text

        # Parse sections marked by ## [SECTION-ID] Title
        sec_matches = list(re.finditer(r"^##\s*\[([^\]]+)\]\s*(.*)", content, re.M))
        for i, match in enumerate(sec_matches):
            sec_id = match.group(1).strip()
            title = match.group(2).strip()
            start = match.end()
            end = sec_matches[i + 1].start() if i + 1 < len(sec_matches) else len(content)
            body = content[start:end].strip()
            
            chunk = KBChunk(
                sec_id=sec_id,
                title=title,
                body=body,
                doc_meta=doc_meta,
                file_name=file_path.name
            )
            self.chunks_by_id[sec_id] = chunk
            self.chunks.append(chunk)

    def get_chunk(self, sec_id: str) -> KBChunk:
        return self.chunks_by_id.get(sec_id)

    def all_chunks(self) -> List[KBChunk]:
        return list(self.chunks)
