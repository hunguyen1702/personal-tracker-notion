from __future__ import annotations

from typing import Any

import mistune

_AST_MARKDOWN = mistune.create_markdown(renderer="ast", plugins=["task_lists"])


def markdown_to_blocks(text: str) -> list[dict[str, Any]]:
    """Convert a markdown string to a list of Notion block dicts."""
    if not text or not text.strip():
        return []
    tokens = _AST_MARKDOWN(text)
    return _flatten([_token_to_block(tok) for tok in tokens])


def _token_to_block(tok: dict[str, Any]) -> list[dict[str, Any]] | dict[str, Any] | None:
    ttype = tok.get("type")
    if ttype == "blank_line":
        return None
    if ttype == "heading":
        level = max(1, min(3, (tok.get("attrs") or {}).get("level", 1)))
        return {
            "object": "block",
            "type": f"heading_{level}",
            f"heading_{level}": {"rich_text": _inline_to_rich_text(tok.get("children") or [])},
        }
    if ttype == "paragraph":
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": _inline_to_rich_text(tok.get("children") or [])},
        }
    if ttype == "block_code":
        info = ((tok.get("attrs") or {}).get("info") or "").strip()
        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{"type": "text", "text": {"content": tok.get("raw", "")}}],
                "language": info or "plain text",
            },
        }
    if ttype == "block_quote":
        return _quote_block(tok.get("children") or [])
    if ttype == "list":
        attrs = tok.get("attrs") or {}
        return _list_items(tok.get("children") or [], ordered=bool(attrs.get("ordered")))
    if ttype == "thematic_break":
        return {"object": "block", "type": "divider", "divider": {}}
    return None


def _flatten(blocks: list[dict[str, Any] | list[dict[str, Any]] | None]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for b in blocks:
        if b is None:
            continue
        if isinstance(b, list):
            out.extend(b)
        else:
            out.append(b)
    return out


def _quote_block(children: list[dict[str, Any]]) -> dict[str, Any] | None:
    rich_text: list[dict[str, Any]] = []
    nested: list[dict[str, Any]] = []
    for child in children:
        if not rich_text and child.get("type") == "paragraph":
            rich_text = _inline_to_rich_text(child.get("children") or [])
            continue
        block = _token_to_block(child)
        if block is not None:
            nested.append(block)
    if not rich_text and not nested:
        return None
    return {
        "object": "block",
        "type": "quote",
        "quote": {"rich_text": rich_text, "children": nested},
    }


def _list_items(items: list[dict[str, Any]], *, ordered: bool) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        if item.get("type") == "task_list_item":
            checked = bool((item.get("attrs") or {}).get("checked"))
            rich_text = _extract_item_rich_text(item.get("children") or [])
            out.append(
                {
                    "object": "block",
                    "type": "to_do",
                    "to_do": {"rich_text": rich_text, "checked": checked},
                }
            )
            continue
        block_type = "numbered_list_item" if ordered else "bulleted_list_item"
        rich_text = _extract_item_rich_text(item.get("children") or [])
        out.append(
            {
                "object": "block",
                "type": block_type,
                block_type: {"rich_text": rich_text},
            }
        )
    return out


def _extract_item_rich_text(children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for child in children:
        if child.get("type") in {"block_text", "paragraph"}:
            return _inline_to_rich_text(child.get("children") or [])
    return _inline_to_rich_text(children)


def _inline_to_rich_text(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw_fragments: list[dict[str, Any]] = []
    for tok in tokens:
        ttype = tok.get("type")
        if ttype == "text":
            raw_fragments.append(_text_fragment(tok.get("raw", "")))
        elif ttype in {"soft_break", "linebreak"}:
            raw_fragments.append(_text_fragment("\n"))
        elif ttype in {"strong", "emphasis"}:
            nested = _inline_to_rich_text(tok.get("children") or [])
            ann_key = "bold" if ttype == "strong" else "italic"
            for frag in nested:
                frag.setdefault("annotations", _empty_annotations())[ann_key] = True
            raw_fragments.extend(nested)
        elif ttype == "codespan":
            raw_fragments.append(
                {
                    "type": "text",
                    "text": {"content": tok.get("raw", "")},
                    "annotations": {**_empty_annotations(), "code": True},
                }
            )
        elif ttype == "link":
            url = (tok.get("attrs") or {}).get("url", "")
            for frag in _inline_to_rich_text(tok.get("children") or []):
                frag["text"]["link"] = {"url": url}
                raw_fragments.append(frag)
        elif ttype == "image":
            continue
        elif ttype == "inline_html":
            raw_fragments.append(_text_fragment(tok.get("raw", "")))
        else:
            raw = tok.get("raw")
            if raw:
                raw_fragments.append(_text_fragment(raw))
    return _merge_adjacent(raw_fragments)


def _empty_annotations() -> dict[str, bool]:
    return {
        "bold": False,
        "italic": False,
        "strikethrough": False,
        "underline": False,
        "code": False,
    }


def _text_fragment(content: str) -> dict[str, Any]:
    return {"type": "text", "text": {"content": content}, "annotations": _empty_annotations()}


def _merge_adjacent(frags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(frags) < 2:
        return frags
    merged: list[dict[str, Any]] = [frags[0]]
    for frag in frags[1:]:
        prev = merged[-1]
        if (
            prev.get("annotations") == frag.get("annotations")
            and prev.get("text", {}).get("link") == frag.get("text", {}).get("link")
        ):
            prev["text"]["content"] += frag["text"]["content"]
        else:
            merged.append(frag)
    return merged
