"""Parse, verify and locate citations emitted by the LLM.

The model returns a prose answer followed by a ``<<<CITATIONS>>>`` marker and a
JSON block describing the documents and verbatim quotes it relied on. We do not
trust those citations blindly: every quote is checked against the actual source
text, and its page number is derived from the ``--- Page N ---`` markers in the
extracted text. A quote that cannot be found is surfaced as *unverified* — the
strongest signal we can give a lawyer that the model may have made something up.
"""

from __future__ import annotations

import json
import re
from typing import TypedDict

import structlog

from takehome.services.llm import CITATION_MARKER

logger = structlog.get_logger()

_PAGE_RE = re.compile(r"---\s*Page\s+(\d+)\s*---")
_WS_RE = re.compile(r"\s+")


class DocPayload(TypedDict):
    id: str
    filename: str
    text: str


class Citation(TypedDict):
    document_id: str | None
    document_name: str
    quote: str
    label: str | None
    page: int | None
    verified: bool


class ResponseAnalysis(TypedDict):
    answer: str
    grounded: bool | None
    confidence: str | None
    citations: list[Citation]


def _normalize(text: str) -> str:
    """Collapse whitespace and lower-case so quote matching is robust to PDF
    line wrapping and minor spacing differences."""
    return _WS_RE.sub(" ", text).strip().lower()


def split_answer(full_text: str) -> tuple[str, str | None]:
    """Split the model output into (prose answer, raw citation JSON or None)."""
    if CITATION_MARKER in full_text:
        answer, _, trailer = full_text.partition(CITATION_MARKER)
        return answer.strip(), trailer.strip()
    return full_text.strip(), None


def find_quote_page(extracted_text: str, quote: str) -> int | None:
    """Return the 1-based page number containing ``quote``, or None if absent.

    Searches page-by-page using the ``--- Page N ---`` markers so the returned
    page is the real PDF page, not an approximation.
    """
    needle = _normalize(quote)
    if not needle:
        return None

    # Split the text into (page_number, page_body) chunks.
    matches = list(_PAGE_RE.finditer(extracted_text))
    if not matches:
        # No page markers — fall back to "found somewhere" without a page.
        return None

    for i, m in enumerate(matches):
        page_num = int(m.group(1))
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(extracted_text)
        body = extracted_text[body_start:body_end]
        if needle in _normalize(body):
            return page_num
    return None


def _verify_citation(
    raw: dict, documents: list[DocPayload]
) -> Citation | None:
    """Verify one raw citation against the documents.

    Locates the quote in the named document; if that fails, searches every
    document (the model sometimes mis-attributes). Returns None for unusable
    input (e.g. an empty quote).
    """
    quote = str(raw.get("quote") or "").strip()
    name = str(raw.get("document") or "").strip()
    label = raw.get("label")
    if not quote:
        return None

    by_name = {d["filename"].lower(): d for d in documents}
    # 1) Try the document the model named.
    named = by_name.get(name.lower())
    if named is None and name:
        # loose match on substring (handles slight filename differences)
        named = next(
            (d for d in documents if name.lower() in d["filename"].lower()
             or d["filename"].lower() in name.lower()),
            None,
        )

    candidates = [named] if named else []
    # 2) Fall back to searching every document, so we can self-correct attribution.
    candidates += [d for d in documents if d not in candidates]

    needle = _normalize(quote)
    for doc in candidates:
        if doc is None:
            continue
        if needle and needle in _normalize(doc["text"]):
            return Citation(
                document_id=doc["id"],
                document_name=doc["filename"],
                quote=quote,
                label=str(label) if label else None,
                page=find_quote_page(doc["text"], quote),
                verified=True,
            )

    # Not found anywhere — surface as unverified against the named document.
    return Citation(
        document_id=named["id"] if named else None,
        document_name=name or (named["filename"] if named else "Unknown document"),
        quote=quote,
        label=str(label) if label else None,
        page=None,
        verified=False,
    )


def analyze_response(full_text: str, documents: list[DocPayload]) -> ResponseAnalysis:
    """Turn raw model output into a clean answer plus verified citations."""
    answer, trailer = split_answer(full_text)

    grounded: bool | None = None
    confidence: str | None = None
    citations: list[Citation] = []

    if trailer:
        # The trailer may be wrapped in a ```json fence; strip it.
        cleaned = trailer.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
        # Be tolerant of trailing prose after the JSON object.
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(cleaned[start : end + 1])
                grounded = data.get("grounded")
                confidence = data.get("confidence")
                for raw in data.get("citations", []) or []:
                    if isinstance(raw, dict):
                        cit = _verify_citation(raw, documents)
                        if cit is not None:
                            citations.append(cit)
            except (json.JSONDecodeError, AttributeError, TypeError):
                logger.warning("Failed to parse citation JSON", trailer=trailer[:500])

    return ResponseAnalysis(
        answer=answer,
        grounded=grounded,
        confidence=confidence,
        citations=citations,
    )
