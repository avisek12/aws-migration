"""
Fetches the environment templates from the public aws-migration GitHub
repo — read-only, no token needed since the repo is public. Never
executes anything from the fetched content; only copies .tf/.md/.example
text files into the download zip for the customer.

Caches the extracted tarball on disk so a burst of chat sessions doesn't
re-download the repo per request (and doesn't hit GitHub's unauthenticated
rate limit); refreshes it once the cache is older than CACHE_TTL_SECONDS.
"""
import io
import os
import tarfile
import tempfile
import threading
import time

import requests

REPO = "avisek12/aws-migration"
BRANCH = "main"
TARBALL_URL = f"https://github.com/{REPO}/archive/refs/heads/{BRANCH}.tar.gz"
CACHE_TTL_SECONDS = 60 * 60  # 1 hour

_lock = threading.Lock()
_cache_dir = None
_cache_time = 0.0


def _download_and_extract() -> str:
    resp = requests.get(TARBALL_URL, timeout=30)
    resp.raise_for_status()
    extract_root = tempfile.mkdtemp(prefix="aws_migration_repo_")
    with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tar:
        tar.extractall(extract_root)  # nosec: content is our own public repo's tarball
    # GitHub tarballs extract into a single "<repo>-<branch>/" subdirectory
    inner = next(
        os.path.join(extract_root, name)
        for name in os.listdir(extract_root)
        if os.path.isdir(os.path.join(extract_root, name))
    )
    return inner


def get_repo_root() -> str:
    """Path to a local checkout of the repo's terraform/ tree, refreshed
    at most once per CACHE_TTL_SECONDS."""
    global _cache_dir, _cache_time
    with _lock:
        if _cache_dir is None or (time.time() - _cache_time) > CACHE_TTL_SECONDS:
            _cache_dir = _download_and_extract()
            _cache_time = time.time()
        return _cache_dir


def get_template_dir(template_dirname: str) -> str:
    root = get_repo_root()
    path = os.path.join(root, "terraform", "environments", template_dirname)
    if not os.path.isdir(path):
        raise FileNotFoundError(f"Template '{template_dirname}' not found in fetched repo at {path}")
    return path
