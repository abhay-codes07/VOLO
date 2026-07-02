"""Framing: incremental ndjson decode must survive any chunking the OS pipe throws at it."""

from __future__ import annotations

import pytest

from volo_mcp import FramingError, MessageBuffer, encode_message


def test_encode_roundtrip() -> None:
    buf = MessageBuffer()
    msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "add"}}
    assert buf.feed(encode_message(msg)) == [msg]


def test_multiple_messages_in_one_chunk() -> None:
    buf = MessageBuffer()
    a = {"jsonrpc": "2.0", "id": 1, "method": "a"}
    b = {"jsonrpc": "2.0", "id": 2, "method": "b"}
    assert buf.feed(encode_message(a) + encode_message(b)) == [a, b]


def test_partial_feed_across_chunk_boundary() -> None:
    buf = MessageBuffer()
    raw = encode_message({"jsonrpc": "2.0", "id": 7, "method": "ping"})
    assert buf.feed(raw[:5]) == []
    assert buf.pending_bytes == 5
    out = buf.feed(raw[5:])
    assert out == [{"jsonrpc": "2.0", "id": 7, "method": "ping"}]
    assert buf.pending_bytes == 0


def test_blank_and_crlf_lines_skipped() -> None:
    buf = MessageBuffer()
    payload = b'\r\n\n{"jsonrpc":"2.0","id":1,"method":"m"}\r\n\n'
    assert buf.feed(payload) == [{"jsonrpc": "2.0", "id": 1, "method": "m"}]


def test_malformed_json_raises() -> None:
    buf = MessageBuffer()
    with pytest.raises(FramingError):
        buf.feed(b"{not json}\n")


def test_non_object_message_raises() -> None:
    buf = MessageBuffer()
    with pytest.raises(FramingError):
        buf.feed(b"[1,2,3]\n")


def test_unicode_survives() -> None:
    buf = MessageBuffer()
    msg = {"jsonrpc": "2.0", "id": 1, "method": "m", "params": {"q": "vólo ✈"}}
    assert buf.feed(encode_message(msg)) == [msg]
