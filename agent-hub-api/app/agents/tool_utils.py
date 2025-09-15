# app/agents/tool_utils.py

from typing import List, Set, Iterable, Optional, Literal
from llama_index.core.tools import BaseTool
import logging
import unicodedata

logger = logging.getLogger(__name__)

def _norm(s: str) -> str:
    """Case/width-insensitive normalization for matching/deduping."""
    return unicodedata.normalize("NFKC", s).casefold()

def _tool_name(tool: BaseTool) -> Optional[str]:
    md = getattr(tool, "metadata", None)
    name = getattr(md, "name", None)
    return name if isinstance(name, str) and name.strip() else None

def _tool_desc(tool: BaseTool) -> str:
    md = getattr(tool, "metadata", None)
    desc = getattr(md, "description", "") or ""
    return desc if isinstance(desc, str) else ""

def dedupe_tools_by_name(
    tools: List[BaseTool],
    *,
    keep: Literal["first", "last"] = "first",
    case_insensitive: bool = True,
) -> List[BaseTool]:
    """
    Return tools with unique names, keeping the first (default) or last occurrence.

    Args:
        tools: input tools
        keep: "first" (stable) or "last" (later overrides earlier)
        case_insensitive: normalize names for dedupe

    Notes:
        - Tools without a usable name are skipped (with a warning).
        - Order is preserved for the kept items.
    """
    if keep not in ("first", "last"):
        raise ValueError("keep must be 'first' or 'last'")

    if keep == "first":
        seen: Set[str] = set()
        unique: List[BaseTool] = []
        for t in tools:
            name = _tool_name(t)
            if not name:
                logger.warning("⚠️ Tool skipped (missing metadata.name): %r", t)
                continue
            key = _norm(name) if case_insensitive else name
            if key not in seen:
                seen.add(key)
                unique.append(t)
        return unique

    # keep == "last": scan from the end then reverse to preserve last occurrence
    seen_last: Set[str] = set()
    kept_rev: List[BaseTool] = []
    for t in reversed(tools):
        name = _tool_name(t)
        if not name:
            logger.warning("⚠️ Tool skipped (missing metadata.name): %r", t)
            continue
        key = _norm(name) if case_insensitive else name
        if key not in seen_last:
            seen_last.add(key)
            kept_rev.append(t)
    kept = list(reversed(kept_rev))
    return kept

def filter_tools_by_keywords(
    tools: List[BaseTool],
    keywords: Iterable[str],
    *,
    mode: Literal["any", "all"] = "any",
    search_in: Literal["name", "name+description"] = "name+description",
    exclude: Iterable[str] = (),
) -> List[BaseTool]:
    """
    Filter tools by keywords.

    Args:
        tools: input tools
        keywords: terms to include (case-insensitive)
        mode: "any" (default) or "all" — how many terms must match
        search_in: search only 'name' or 'name+description'
        exclude: terms that, if present, exclude a tool (case-insensitive)

    Behavior:
        - Matches are substring-based on normalized text.
        - Tools without a usable name are skipped silently.
        - Preserves input order.
    """
    kw = [_norm(k) for k in keywords if isinstance(k, str) and k.strip()]
    ex = [_norm(x) for x in exclude if isinstance(x, str) and x.strip()]

    if not kw and not ex:
        logger.info("🔍 No keywords/exclusions provided; returning empty list.")
        return []

    out: List[BaseTool] = []
    for t in tools:
        name = _tool_name(t)
        if not name:
            continue

        name_n = _norm(name)
        haystack_parts = [name_n]
        if search_in == "name+description":
            haystack_parts.append(_norm(_tool_desc(t)))
        haystack = " \n ".join(haystack_parts)

        # exclusions first
        if ex and any(term in haystack for term in ex):
            logger.debug("🚫 Excluded tool '%s' due to exclude terms %s", name, exclude)
            continue

        if kw:
            matched = [term for term in kw if term in haystack]
            ok = (bool(matched) if mode == "any" else len(matched) == len(kw))
            if not ok:
                continue

        out.append(t)
        logger.debug("✅ Tool '%s' matched (mode=%s, scope=%s)", name, mode, search_in)

    logger.info("🔍 Filtered %d tools from %d (mode=%s, scope=%s, include=%s, exclude=%s)",
                len(out), len(tools), mode, search_in, list(keywords), list(exclude))
    return out
