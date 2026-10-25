"""tests/detect/test_context_resend_signatures.py — thinking signatures weighted
by the thinking they carry.

Locks `docs/CC_SIGNATURE_TOKEN_SHARE_PREREG.md` §1: which chunks qualify,
which models change, how the estimate is taken from the producing call,
and that every other chunk keeps its old count exactly.
"""
from __future__ import annotations

import json

import pytest

from clew.detect.context_resend import (
    _chunk_lengths,
    _chunk_token_len,
    _keeps_thinking,
    _signature_element,
    _text_token_len,
)

SIG = "EqoBCkgIBxABGAIiQL" * 40


def _dump(elem: dict) -> str:
    return json.dumps(elem, sort_keys=True, ensure_ascii=False)


def _assistant(*blocks: dict) -> dict:
    return {"role": "assistant", "content": list(blocks)}


def _thinking(sig: str = SIG) -> dict:
    return {"type": "thinking", "thinking": "", "signature": sig}


USER = {"role": "user", "content": "do the thing"}
ANSWER = _assistant(_thinking(), {"type": "text", "text": "done, see the file"},
                    {"type": "tool_use", "id": "t1", "name": "Read", "input": {"path": "a.py"}})


def _calls(model: str, producer_output, *, second_model: str | None = None) -> list[dict]:
    return [
        {"model": model, "input_text": json.dumps([USER]), "output_tokens": producer_output},
        {"model": second_model or model, "input_text": json.dumps([USER, ANSWER]), "output_tokens": 7},
    ]


def _visible(model: str) -> int:
    return (_text_token_len("done, see the file", model) + _text_token_len("Read", model)
            + _text_token_len(json.dumps({"path": "a.py"}, sort_keys=True), model))


@pytest.mark.parametrize("model, keeps", [
    ("claude-sonnet-4-6", True),
    ("claude-opus-4-8", True),
    ("claude-opus-4-5-20251101", True),
    ("claude-sonnet-4-5", False),
    ("claude-haiku-4-5", False),
    ("claude-3-7-sonnet-20250219", False),
    ("<synthetic>", False),
    (None, False),
])
def test_keeps_thinking_follows_the_documented_rule(model, keeps):
    assert _keeps_thinking(model) is keeps


def test_signature_chunk_needs_assistant_role_and_a_signed_thinking_block():
    assert _signature_element(_dump(ANSWER), "assistant") is not None
    assert _signature_element(_dump(ANSWER), None) is None
    assert _signature_element(_dump(_assistant(_thinking(""))), "assistant") is None
    assert _signature_element(_dump(_assistant({"type": "redacted_thinking", "data": SIG})),
                              "assistant") is None


def test_signature_chunk_weighed_by_the_producing_call():
    model = "claude-opus-4-8"
    lengths = _chunk_lengths(_calls(model, 100))
    text, role, toks = lengths.per_call[1][1]
    stripped = _assistant({"type": "thinking", "thinking": ""},
                          {"type": "text", "text": "done, see the file"},
                          {"type": "tool_use", "id": "t1", "name": "Read", "input": {"path": "a.py"}})
    assert toks == _chunk_token_len(_dump(stripped), model) + 100 - _visible(model)
    assert toks < _chunk_token_len(text, model)
    (sig,) = lengths.signatures.values()
    assert (sig.first_call, sig.source_call, sig.thinking_estimate) == (1, 0, 100 - _visible(model))
    assert lengths.signature_occurrences == {(model, True): 1}


@pytest.mark.parametrize("producer_output", [0, None, "500"])
def test_no_estimate_keeps_the_old_length(producer_output):
    model = "claude-opus-4-8"
    lengths = _chunk_lengths(_calls(model, producer_output))
    text, _, toks = lengths.per_call[1][1]
    assert toks == _chunk_token_len(text, model)
    assert lengths.signature_occurrences == {(model, False): 1}


@pytest.mark.parametrize("model", ["claude-haiku-4-5", "<synthetic>"])
def test_model_that_does_not_keep_thinking_keeps_the_old_length(model):
    lengths = _chunk_lengths(_calls("claude-opus-4-8", 500, second_model=model))
    text, _, toks = lengths.per_call[1][1]
    assert toks == _chunk_token_len(text, model)


def test_first_appearance_in_call_zero_has_no_estimate():
    model = "claude-opus-4-8"
    calls = [{"model": model, "input_text": json.dumps([USER, ANSWER]), "output_tokens": 9}]
    text, _, toks = _chunk_lengths(calls).per_call[0][1]
    assert toks == _chunk_token_len(text, model)


def test_estimate_never_negative():
    model = "claude-opus-4-8"
    lengths = _chunk_lengths(_calls(model, 1))
    (sig,) = lengths.signatures.values()
    assert sig.thinking_estimate == 0


def test_every_other_chunk_keeps_its_old_count():
    model = "claude-opus-4-8"
    calls = _calls(model, 500)
    for per_call, call in zip(_chunk_lengths(calls).per_call, calls):
        for text, role, toks in per_call:
            if _signature_element(text, role) is None:
                assert toks == _chunk_token_len(text, model)


def test_whole_input_fallback_is_not_a_signature_chunk():
    model = "claude-opus-4-8"
    calls = [{"model": model, "input_text": "x", "output_tokens": 500},
             {"model": model, "input_text": _dump(ANSWER), "output_tokens": 7}]
    text, role, toks = _chunk_lengths(calls).per_call[1][0]
    assert role is None and toks == _chunk_token_len(text, model)
