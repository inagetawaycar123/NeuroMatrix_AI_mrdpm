import math
import os
import re
import threading
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from pypdf import PdfReader


_CACHE_LOCK = threading.Lock()
_INDEX_CACHE: Dict[str, Any] = {
    "key": None,
    "chunks": [],
    "idf": {},
}


@dataclass
class EvidenceChunk:
    evidence_id: str
    doc_name: str
    page: int
    text: str
    norm_text: str
    token_counter: Counter


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_ekv_docs_dir() -> str:
    return os.path.join(_project_root(), "EKV_docs")


def _normalize_text(text: str) -> str:
    s = str(text or "")
    s = s.replace("\u3000", " ").lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _extract_zh_bigrams(text: str) -> List[str]:
    chars = re.findall(r"[\u4e00-\u9fff]", str(text or ""))
    if len(chars) < 2:
        return chars
    return ["".join(chars[i : i + 2]) for i in range(len(chars) - 1)]


def _extract_en_tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_]{2,}", str(text or "").lower())


def _extract_tokens(text: str) -> Counter:
    return Counter(_extract_zh_bigrams(text) + _extract_en_tokens(text))


def _split_page_to_chunks(page_text: str, max_chars: int = 520) -> List[str]:
    text = str(page_text or "").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return []
    joined = "\n".join(lines)
    parts = re.split(r"(?<=[\u3002\uff01\uff1f!?])\s+|\n{2,}", joined)
    parts = [p.strip() for p in parts if p and p.strip()]
    if not parts:
        parts = [joined]

    chunks: List[str] = []
    buf = ""
    for part in parts:
        candidate = (buf + " " + part).strip() if buf else part
        if len(candidate) <= max_chars:
            buf = candidate
            continue
        if buf:
            chunks.append(buf)
        if len(part) <= max_chars:
            buf = part
            continue
        start = 0
        while start < len(part):
            chunks.append(part[start : start + max_chars])
            start += max_chars
        buf = ""
    if buf:
        chunks.append(buf)
    return chunks


def _collect_pdf_files(docs_dir: str) -> List[str]:
    if not os.path.isdir(docs_dir):
        return []
    files = []
    for name in sorted(os.listdir(docs_dir)):
        if name.lower().endswith(".pdf"):
            files.append(os.path.join(docs_dir, name))
    return files


def _index_key(files: Sequence[str]) -> Tuple[Tuple[str, int, int], ...]:
    key_items = []
    for path in files:
        try:
            st = os.stat(path)
            key_items.append((os.path.basename(path), int(st.st_mtime), int(st.st_size)))
        except Exception:
            key_items.append((os.path.basename(path), 0, 0))
    return tuple(key_items)


def _build_index(files: Sequence[str]) -> Tuple[List[EvidenceChunk], Dict[str, float]]:
    chunks: List[EvidenceChunk] = []
    doc_freq: Dict[str, int] = defaultdict(int)

    for pdf_path in files:
        try:
            reader = PdfReader(pdf_path)
        except Exception:
            continue

        doc_name = os.path.basename(pdf_path)
        for page_idx, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            if not page_text.strip():
                continue

            for raw_chunk in _split_page_to_chunks(page_text):
                norm_text = _normalize_text(raw_chunk)
                token_counter = _extract_tokens(norm_text)
                if not token_counter:
                    continue
                chunk = EvidenceChunk(
                    evidence_id=str(uuid.uuid4()),
                    doc_name=doc_name,
                    page=page_idx + 1,
                    text=raw_chunk.strip(),
                    norm_text=norm_text,
                    token_counter=token_counter,
                )
                chunks.append(chunk)
                for token in token_counter.keys():
                    doc_freq[token] += 1

    total_chunks = max(1, len(chunks))
    idf: Dict[str, float] = {}
    for token, df in doc_freq.items():
        idf[token] = math.log((total_chunks + 1.0) / (df + 1.0)) + 1.0
    return chunks, idf


def _ensure_index(force_rebuild: bool = False) -> Tuple[List[EvidenceChunk], Dict[str, float]]:
    docs_dir = get_ekv_docs_dir()
    files = _collect_pdf_files(docs_dir)
    key = _index_key(files)

    with _CACHE_LOCK:
        if (
            not force_rebuild
            and _INDEX_CACHE.get("key") == key
            and _INDEX_CACHE.get("chunks")
        ):
            return _INDEX_CACHE["chunks"], _INDEX_CACHE["idf"]

        chunks, idf = _build_index(files)
        _INDEX_CACHE["key"] = key
        _INDEX_CACHE["chunks"] = chunks
        _INDEX_CACHE["idf"] = idf
        return chunks, idf


def _claim_query_spec(claim_id: str, claim_text: str, message: str) -> Dict[str, Any]:
    cid = str(claim_id or "").strip()
    base = f"{claim_text or ''} {message or ''}".strip()

    specs = {
        "hemisphere": {
            "query": f"{base} laterality hemisphere \u504f\u4fa7 \u5de6\u4fa7 \u53f3\u4fa7 \u53cc\u4fa7",
            "must_terms": ["\u504f\u4fa7", "laterality", "hemisphere"],
        },
        "core_infarct_volume": {
            "query": (
                f"{base} core infarct volume ctp cbf cbv tmax "
                "\u6838\u5fc3 \u6897\u6b7b \u4f53\u79ef \u704c\u6ce8"
            ),
            "must_terms": ["\u6838\u5fc3", "core", "volume", "ctp"],
        },
        "penumbra_volume": {
            "query": (
                f"{base} penumbra volume ctp perfusion "
                "\u534a\u6697\u5e26 \u4f53\u79ef \u704c\u6ce8"
            ),
            "must_terms": ["\u534a\u6697\u5e26", "penumbra", "volume", "ctp"],
        },
        "mismatch_ratio": {
            "query": (
                f"{base} mismatch ratio core penumbra perfusion "
                "\u4e0d\u5339\u914d \u6bd4\u503c \u6bd4\u4f8b"
            ),
            "must_terms": ["\u4e0d\u5339\u914d", "mismatch", "ratio"],
        },
        "significant_mismatch": {
            "query": (
                f"{base} significant mismatch salvageable tissue "
                "\u663e\u8457\u4e0d\u5339\u914d \u53ef\u632d\u6551 \u7ec4\u7ec7"
            ),
            "must_terms": ["\u4e0d\u5339\u914d", "mismatch", "\u632d\u6551"],
        },
        "treatment_window_notice": {
            "query": (
                f"{base} treatment window onset admission 6h 24h thrombectomy "
                "\u65f6\u95f4\u7a97 \u53d1\u75c5 \u5165\u9662 \u53d6\u6813"
            ),
            "must_terms": ["\u65f6\u95f4\u7a97", "window", "onset", "admission"],
        },
    }
    return specs.get(cid, {"query": base, "must_terms": []})


def _score_chunk(
    query_counter: Counter,
    must_terms: List[str],
    chunk: EvidenceChunk,
    idf: Dict[str, float],
) -> float:
    score = 0.0
    for token, qtf in query_counter.items():
        ctf = chunk.token_counter.get(token, 0)
        if ctf <= 0:
            continue
        score += float(qtf) * (1.0 + math.log(1.0 + ctf)) * idf.get(token, 1.0)

    if must_terms:
        hits = 0
        for term in must_terms:
            t = str(term or "").strip().lower()
            if t and t in chunk.norm_text:
                hits += 1
        score += hits * 1.5
        if hits == 0 and score < 1.0:
            return 0.0
    return score


def search_guideline_evidence(
    claim_id: str,
    claim_text: str,
    message: str = "",
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    chunks, idf = _ensure_index()
    if not chunks:
        return []

    spec = _claim_query_spec(claim_id, claim_text, message)
    query = str(spec.get("query") or "").strip()
    must_terms = [str(x or "").strip() for x in (spec.get("must_terms") or []) if str(x or "").strip()]
    query_counter = _extract_tokens(_normalize_text(query))
    if not query_counter:
        return []

    scored: List[Tuple[float, EvidenceChunk]] = []
    for chunk in chunks:
        score = _score_chunk(query_counter, must_terms, chunk, idf)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[: max(1, int(top_k))]

    results: List[Dict[str, Any]] = []
    for _, item in top:
        snippet = item.text.strip()
        if len(snippet) > 260:
            snippet = snippet[:260] + "..."
        results.append(
            {
                "evidence_id": item.evidence_id,
                "source_type": "guideline_pdf",
                "source_ref": f"{item.doc_name}#page={item.page}",
                "doc_name": item.doc_name,
                "page": item.page,
                "snippet": snippet,
            }
        )
    return results
