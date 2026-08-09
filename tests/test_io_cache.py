"""Tests for baseball_lab.io.cache."""

import pytest
import requests

from baseball_lab.io import cache
from baseball_lab.io.cache import FetchError, cached_get_json, cached_get_text


class _Resp:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text


def test_cache_hit_never_touches_network(tmp_path, monkeypatch):
    path = tmp_path / "cached.json"
    path.write_text('{"cached": true}')

    def boom(*args, **kwargs):
        raise AssertionError("network was called on a cache hit")

    monkeypatch.setattr(requests, "get", boom)
    assert cached_get_json("https://example.invalid/x", cache_path=path) == {"cached": True}


def test_fetch_writes_cache(tmp_path, monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return _Resp(200, '{"ok": 1}')

    monkeypatch.setattr(requests, "get", fake_get)
    path = tmp_path / "sub" / "resp.json"
    assert cached_get_json("https://example.invalid/x", cache_path=path) == {"ok": 1}
    assert path.read_text() == '{"ok": 1}'
    # Second call is served from cache
    assert cached_get_json("https://example.invalid/x", cache_path=path) == {"ok": 1}
    assert len(calls) == 1


def test_force_refetches(tmp_path, monkeypatch):
    path = tmp_path / "resp.txt"
    path.write_text("stale")
    monkeypatch.setattr(requests, "get", lambda url, **kw: _Resp(200, "fresh"))
    assert cached_get_text("https://example.invalid/x", cache_path=path, force=True) == "fresh"
    assert path.read_text() == "fresh"


def test_4xx_fails_fast(tmp_path, monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return _Resp(404, "not found")

    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(FetchError, match="HTTP 404"):
        cached_get_text("https://example.invalid/x", cache_path=tmp_path / "x.txt")
    assert len(calls) == 1
    assert not (tmp_path / "x.txt").exists()


def test_5xx_retries_then_raises(tmp_path, monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return _Resp(500, "boom")

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(cache.time, "sleep", lambda s: None)
    with pytest.raises(FetchError, match="failed after 3 attempts"):
        cached_get_text("https://example.invalid/x", cache_path=tmp_path / "x.txt")
    assert len(calls) == 3


def test_invalid_json_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("not json {")
    with pytest.raises(FetchError, match="Invalid JSON"):
        cached_get_json("https://example.invalid/x", cache_path=path)
