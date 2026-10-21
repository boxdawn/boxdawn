"""tests/detect/test_context_resend_images.py — image blocks weighted as billed.

Locks `docs/CC_IMAGE_TOKEN_SHARE_PREREG.md` §1: the documented resize
examples, the tier rule, the header reader, and that a chunk without a
readable image keeps its old count exactly.
"""
from __future__ import annotations

import base64
import json
import struct

import pytest

from clew.detect.context_resend import (
    _chunk_token_len,
    _image_size,
    _model_version,
    _resized_size,
    _text_token_len,
    _visual_tokens,
)


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _png(w: int, h: int) -> str:
    return _b64(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", w, h)
                + b"\x08\x02\x00\x00\x00" + b"\x00" * 64)


def _gif(w: int, h: int) -> str:
    return _b64(b"GIF89a" + struct.pack("<HH", w, h) + b"\x00" * 64)


def _webp_vp8x(w: int, h: int) -> str:
    return _b64(b"RIFF\x00\x00\x00\x00WEBPVP8X" + b"\x0a\x00\x00\x00" + b"\x00" * 4
                + (w - 1).to_bytes(3, "little") + (h - 1).to_bytes(3, "little") + b"\x00" * 64)


def _jpeg(w: int, h: int) -> str:
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x00" * 9
    dht = b"\xff\xc4" + struct.pack(">H", 4) + b"\x00\x00"
    sof0 = b"\xff\xc0" + struct.pack(">HBHH", 11, 8, h, w) + b"\x01\x01\x11\x00"
    return _b64(b"\xff\xd8" + app0 + dht + sof0 + b"\x00" * 64)


def _msg(*blocks: dict) -> str:
    return json.dumps({"role": "user", "content": list(blocks)}, sort_keys=True, ensure_ascii=False)


def _image(data: str) -> dict:
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}}


# ── documented examples (vision / vision-coordinates, read 2026-10-21) ───────

@pytest.mark.parametrize("size, limits, expected", [
    ((1075, 1520), (1568, 1568), (924, 1307)),
    ((1920, 1080), (1568, 1568), (1456, 819)),
    ((200, 200), (1568, 1568), (200, 200)),
    ((3840, 2160), (2576, 4784), (2576, 1449)),
    ((1920, 1080), (2576, 4784), (1920, 1080)),
])
def test_resized_size_matches_documented_examples(size, limits, expected):
    assert _resized_size(*size, *limits) == expected


@pytest.mark.parametrize("size, model, tokens", [
    ((1920, 1080), "claude-sonnet-4-6", 1560),
    ((200, 200), "claude-sonnet-4-6", 64),
    ((1920, 1080), "claude-opus-4-8", 2691),
    ((3840, 2160), "claude-opus-4-8", 4784),
])
def test_visual_tokens_match_documented_examples(size, model, tokens):
    assert _visual_tokens(*size, model) == tokens


# ── tier rule (§1.4) ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("model, version", [
    ("claude-sonnet-4-6", (4, 6)),
    ("claude-opus-4-7", (4, 7)),
    ("claude-opus-4.8", (4, 8)),
    ("claude-opus-5", (5, 0)),
    ("claude-mythos-5-1", (5, 1)),
    ("claude-fable-5", (5, 0)),
    ("claude-sonnet-4-20250514", (4, 0)),
    ("claude-3-5-sonnet", (3, 5)),
    ("claude-4.5-haiku-1001", (4, 5)),
    ("claude-opus-4-8[1m]", (4, 8)),
    ("us.anthropic.claude-opus-4-8-v1:0", (4, 8)),
    ("claude-haiku-5-5 (>100k)", (5, 5)),
    ("<synthetic>", None),
])
def test_model_version(model, version):
    assert _model_version(model) == version


# ── header reader (§1.3) ─────────────────────────────────────────────────────

@pytest.mark.parametrize("data", [_png(1366, 768), _gif(1366, 768), _webp_vp8x(1366, 768), _jpeg(1366, 768)])
def test_image_size_reads_each_format(data):
    assert _image_size(data) == (1366, 768)


@pytest.mark.parametrize("data", ["not base64 at all!", _b64(b"plain text, no image header"), ""])
def test_image_size_unreadable_is_none(data):
    assert _image_size(data) is None


# ── chunk length (§1.1, §1.6) ────────────────────────────────────────────────

def test_chunk_without_image_keeps_its_count():
    chunk = _msg({"type": "text", "text": "hello " * 50})
    assert _chunk_token_len(chunk, "claude-opus-4-8") == _text_token_len(chunk, "claude-opus-4-8")


def test_image_chunk_is_text_without_image_plus_visual_tokens():
    chunk = _msg({"type": "text", "text": "look"}, _image(_png(1920, 1080)))
    rest = _msg({"type": "text", "text": "look"})
    assert _chunk_token_len(chunk, "claude-sonnet-4-6") == _text_token_len(rest, "claude-sonnet-4-6") + 1560
    assert _chunk_token_len(chunk, "claude-opus-4-8") == _text_token_len(rest, "claude-opus-4-8") + 2691


def test_image_nested_in_tool_result_is_weighted():
    chunk = _msg({"type": "tool_result", "tool_use_id": "t1", "content": [_image(_png(200, 200))]})
    rest = _msg({"type": "tool_result", "tool_use_id": "t1", "content": []})
    assert _chunk_token_len(chunk, "claude-sonnet-4-6") == _text_token_len(rest, "claude-sonnet-4-6") + 64


def test_non_claude_model_is_unchanged():
    chunk = _msg(_image(_png(1920, 1080)))
    assert _chunk_token_len(chunk, "gpt-4o") == _text_token_len(chunk, "gpt-4o")
    assert _chunk_token_len(chunk, None) == _text_token_len(chunk, None)


def test_unreadable_image_is_counted_as_before():
    chunk = _msg(_image(_b64(b"no header here" * 20)))
    assert _chunk_token_len(chunk, "claude-opus-4-8") == _text_token_len(chunk, "claude-opus-4-8")


def test_text_not_in_canonical_form_is_unchanged():
    # The raw-text fallback chunk of _chunk_boundary is not re-serialized.
    chunk = json.dumps({"role": "user", "content": [_image(_png(1920, 1080))]})  # role before content
    assert chunk != json.dumps(json.loads(chunk), sort_keys=True, ensure_ascii=False)
    assert _chunk_token_len(chunk, "claude-opus-4-8") == _text_token_len(chunk, "claude-opus-4-8")
