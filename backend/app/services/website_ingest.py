from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "KlyroAI-IngestBot/1.0 (+https://example.com)",
    "Accept": "text/html,application/xhtml+xml",
}


@dataclass(frozen=True)
class PageContent:
    url: str
    text: str


def _strip_www(host: str) -> str:
    h = host.lower()
    if h.startswith("www."):
        return h[4:]
    return h


def same_registrable_domain(base_url: str, candidate_url: str) -> bool:
    b = urlparse(base_url)
    c = urlparse(candidate_url)
    if b.scheme not in ("http", "https") or c.scheme not in ("http", "https"):
        return False
    return _strip_www(b.netloc) == _strip_www(c.netloc)


def _canonical_visit_key(url: str) -> str:
    u, _frag = urldefrag(url)
    p = urlparse(u)
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return f"{p.scheme.lower()}://{_strip_www(p.netloc)}{path}".lower()


def _normalize_link(base_url: str, href: str) -> str | None:
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    joined = urljoin(base_url, href)
    joined, _ = urldefrag(joined)
    p = urlparse(joined)
    if p.scheme not in ("http", "https"):
        return None
    if not p.netloc:
        return None
    return joined


def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = (ln.strip() for ln in text.splitlines())
    return "\n".join(ln for ln in lines if ln)


def chunk_words(
    text: str,
    min_words: int | None = None,
    max_words: int | None = None,
) -> list[str]:
    min_w = min_words if min_words is not None else settings.ingest_chunk_min_words
    max_w = max_words if max_words is not None else settings.ingest_chunk_max_words
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    i = 0
    n = len(words)
    while i < n:
        take = min(max_w, n - i)
        chunk = words[i : i + take]
        i += take
        chunks.append(" ".join(chunk))
    if len(chunks) >= 2:
        last_n = len(chunks[-1].split())
        if last_n < min_w:
            merged = chunks[-2] + " " + chunks[-1]
            merged_n = len(merged.split())
            if merged_n <= max_w:
                chunks = chunks[:-2] + [merged]
    return [c for c in chunks if c.strip()]


def fetch_html(session: requests.Session, url: str, timeout: float) -> str | None:
    try:
        r = session.get(url, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "text/html" not in ctype and "application/xhtml" not in ctype:
            logger.debug("Skip non-HTML %s (%s)", url, ctype)
            return None
        if r.encoding is None or r.encoding == "ISO-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        return r.text
    except requests.RequestException as e:
        logger.warning("Fetch failed %s: %s", url, e)
        return None


def extract_same_domain_links(html: str, page_url: str, seed_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        norm = _normalize_link(page_url, a["href"])
        if norm is None:
            continue
        if not same_registrable_domain(seed_url, norm):
            continue
        key = _canonical_visit_key(norm)
        if key in seen:
            continue
        seen.add(key)
        out.append(norm)
    return out


def crawl_site(
    start_url: str,
    *,
    max_depth: int | None = None,
    max_pages: int | None = None,
    timeout: float | None = None,
) -> list[PageContent]:
    max_d = max_depth if max_depth is not None else settings.ingest_max_depth
    max_p = max_pages if max_pages is not None else settings.ingest_max_pages
    to = timeout if timeout is not None else settings.ingest_request_timeout_seconds

    start_url, _ = urldefrag(start_url.strip())
    if urlparse(start_url).scheme not in ("http", "https"):
        raise ValueError("start_url must be http(s)")

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    visited_keys: set[str] = set()
    results: list[PageContent] = []
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])

    while queue and len(results) < max_p:
        url, depth = queue.popleft()
        key = _canonical_visit_key(url)
        if key in visited_keys:
            continue
        visited_keys.add(key)

        html = fetch_html(session, url, to)
        if html is None:
            continue

        text = extract_visible_text(html)
        if text.strip():
            results.append(PageContent(url=url, text=text.strip()))

        if depth >= max_d:
            continue

        for link in extract_same_domain_links(html, url, start_url):
            lk = _canonical_visit_key(link)
            if lk not in visited_keys:
                queue.append((link, depth + 1))

    return results


def build_chunk_records(pages: list[PageContent]) -> list[tuple[str, int, str]]:
    """Return (source_url, chunk_index, content) in order."""
    records: list[tuple[str, int, str]] = []
    idx = 0
    for page in pages:
        for chunk in chunk_words(page.text):
            records.append((page.url, idx, chunk))
            idx += 1
    return records


def ingest_website(start_url: str) -> tuple[list[PageContent], list[tuple[str, int, str]]]:
    pages = crawl_site(start_url)
    chunks = build_chunk_records(pages)
    return pages, chunks
