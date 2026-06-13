from __future__ import annotations

from personal_tracker.notion.blocks import markdown_to_blocks


def _rich_text(blocks: list[dict]) -> list[dict]:
    return blocks[0]["paragraph"]["rich_text"]


def test_empty_string_returns_empty_list():
    assert markdown_to_blocks("") == []


def test_whitespace_only_returns_empty_list():
    assert markdown_to_blocks("   \n\n  \n") == []


def test_plain_paragraph():
    blocks = markdown_to_blocks("hello world")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "paragraph"
    rt = _rich_text(blocks)
    assert rt[0]["text"]["content"] == "hello world"


def test_heading_levels():
    blocks = markdown_to_blocks("# H1\n\n## H2\n\n### H3\n\n#### H4")
    types = [b["type"] for b in blocks]
    assert types == ["heading_1", "heading_2", "heading_3", "heading_3"]


def test_bulleted_list_each_item_is_separate_block():
    blocks = markdown_to_blocks("- a\n- b\n- c")
    assert len(blocks) == 3
    for b in blocks:
        assert b["type"] == "bulleted_list_item"
    contents = [b["bulleted_list_item"]["rich_text"][0]["text"]["content"] for b in blocks]
    assert contents == ["a", "b", "c"]


def test_numbered_list():
    blocks = markdown_to_blocks("1. x\n2. y")
    assert [b["type"] for b in blocks] == ["numbered_list_item", "numbered_list_item"]


def test_code_block_with_language():
    blocks = markdown_to_blocks("```python\nprint(1)\n```")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "code"
    assert blocks[0]["code"]["language"] == "python"
    assert blocks[0]["code"]["rich_text"][0]["text"]["content"] == "print(1)\n"


def test_code_block_without_language_defaults_to_plain_text():
    blocks = markdown_to_blocks("```\nfoo\n```")
    assert blocks[0]["code"]["language"] == "plain text"


def test_quote_block_promotes_inline_to_rich_text():
    blocks = markdown_to_blocks("> quoted text")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "quote"
    rt = blocks[0]["quote"]["rich_text"]
    assert rt[0]["text"]["content"] == "quoted text"
    assert blocks[0]["quote"]["children"] == []


def test_quote_block_with_multi_paragraph_children():
    blocks = markdown_to_blocks("> first\n>\n> second")
    assert blocks[0]["type"] == "quote"
    assert blocks[0]["quote"]["rich_text"][0]["text"]["content"] == "first"


def test_divider():
    blocks = markdown_to_blocks("---")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "divider"
    assert blocks[0]["divider"] == {}


def test_inline_bold():
    blocks = markdown_to_blocks("**hi**")
    rt = _rich_text(blocks)
    assert rt[0]["text"]["content"] == "hi"
    assert rt[0]["annotations"]["bold"] is True


def test_inline_italic():
    blocks = markdown_to_blocks("*hi*")
    rt = _rich_text(blocks)
    assert rt[0]["text"]["content"] == "hi"
    assert rt[0]["annotations"]["italic"] is True


def test_inline_code():
    blocks = markdown_to_blocks("`snippet`")
    rt = _rich_text(blocks)
    assert rt[0]["text"]["content"] == "snippet"
    assert rt[0]["annotations"]["code"] is True


def test_inline_link():
    blocks = markdown_to_blocks("[label](https://example.com)")
    rt = _rich_text(blocks)
    assert rt[0]["text"]["content"] == "label"
    assert rt[0]["text"]["link"]["url"] == "https://example.com"


def test_image_is_dropped():
    blocks = markdown_to_blocks("![alt](https://x.com/y.png)")
    rt = _rich_text(blocks)
    assert all("link" not in (frag.get("text") or {}) for frag in rt)


def test_task_list_to_do_blocks():
    blocks = markdown_to_blocks("- [ ] one\n- [x] two")
    assert len(blocks) == 2
    assert blocks[0]["type"] == "to_do"
    assert blocks[0]["to_do"]["checked"] is False
    assert blocks[0]["to_do"]["rich_text"][0]["text"]["content"] == "one"
    assert blocks[1]["to_do"]["checked"] is True


def test_mixed_blocks_preserve_order():
    md = "# Title\n\nintro\n\n- one\n- two\n\n```\ncode\n```\n\n> quote"
    blocks = markdown_to_blocks(md)
    types = [b["type"] for b in blocks]
    assert types == [
        "heading_1",
        "paragraph",
        "bulleted_list_item",
        "bulleted_list_item",
        "code",
        "quote",
    ]


def test_merged_annotations_collapse_adjacent_text():
    blocks = markdown_to_blocks("plain text")
    rt = _rich_text(blocks)
    assert len(rt) == 1
    assert rt[0]["text"]["content"] == "plain text"
    assert rt[0]["annotations"]["bold"] is False
