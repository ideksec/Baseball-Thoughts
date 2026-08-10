"""Cache-first HTTP fetching.

Every fetch is keyed to a cache path under data/raw/. If the cache file
exists, it is read from disk and the network is never touched — this keeps
request volume polite and makes analyses reproducible. Failures raise
FetchError; there are no silent failures.
"""

import json
import time
from pathlib import Path

import requests

USER_AGENT = "baseball-lab (github.com/ideksec/Baseball-Thoughts)"
DEFAULT_TIMEOUT = 30.0
DATA_RAW = Path("data/raw")


class FetchError(RuntimeError):
    """A network fetch failed after retries, or returned an error status."""


def _fetch(
    url: str,
    params: dict | None,
    timeout: float,
    max_retries: int,
) -> requests.Response:
    """GET with exponential backoff on 5xx and network errors. 4xx fails fast."""
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(
                url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT}
            )
            if 400 <= resp.status_code < 500:
                raise FetchError(f"HTTP {resp.status_code} from {url}")
            if resp.status_code >= 500:
                last_err = RuntimeError(f"HTTP {resp.status_code} from {url}")
            else:
                return resp
        except FetchError:
            raise
        except requests.RequestException as err:
            last_err = err
        if attempt < max_retries - 1:
            time.sleep(2**attempt)
    raise FetchError(f"GET {url} failed after {max_retries} attempts: {last_err}")


def _write_atomic(cache_path: Path, content: str) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_suffix(cache_path.suffix + ".tmp")
    tmp.write_text(content)
    tmp.rename(cache_path)


def cached_get_text(
    url: str,
    *,
    params: dict | None = None,
    cache_path: Path,
    force: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = 3,
) -> str:
    """Return response text, reading from cache_path when it exists."""
    if cache_path.exists() and not force:
        return cache_path.read_text()
    resp = _fetch(url, params, timeout, max_retries)
    _write_atomic(cache_path, resp.text)
    return resp.text


def cached_get_json(
    url: str,
    *,
    params: dict | None = None,
    cache_path: Path,
    force: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = 3,
) -> dict:
    """Return parsed JSON, reading from cache_path when it exists."""
    text = cached_get_text(
        url,
        params=params,
        cache_path=cache_path,
        force=force,
        timeout=timeout,
        max_retries=max_retries,
    )
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        raise FetchError(f"Invalid JSON from {url} (cache: {cache_path}): {err}") from err
