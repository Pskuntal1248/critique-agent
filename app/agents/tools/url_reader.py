"""URL reader tool — fetches and extracts clean text from a web page."""

import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Tags whose content we strip entirely
_REMOVE_TAGS = {"script", "style", "nav", "footer", "header", "aside", "form"}
_MAX_CHARS = 8000  # truncate to keep token usage reasonable
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MB hard cap
_ALLOWED_SCHEMES = {"http", "https"}
_ALLOWED_CONTENT_TYPES = {"text/html", "text/plain"}

# Private IPv4 ranges + cloud metadata endpoint blocked to prevent SSRF
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / cloud metadata
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _is_private_host(hostname: str) -> bool:
    """Return True if the hostname resolves to a private or loopback address."""
    try:
        addr = ipaddress.ip_address(socket.gethostbyname(hostname))
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except Exception:
        # If we cannot resolve, block it to be safe
        return True


def _validate_url(url: str) -> str | None:
    """Return an error message if the URL is not safe, else None."""
    try:
        parsed = urlparse(url)
    except Exception:
        return "Invalid URL"

    if parsed.scheme not in _ALLOWED_SCHEMES:
        return f"Scheme '{parsed.scheme}' not allowed; use http or https"

    hostname = parsed.hostname or ""
    if not hostname:
        return "Missing hostname"

    if _is_private_host(hostname):
        return f"Host '{hostname}' resolves to a private or reserved address (SSRF protection)"

    return None


@tool
def url_reader(url: str) -> dict:
    """Fetch a URL and extract readable text content.

    Args:
        url: The full URL to fetch and parse.

    Returns:
        Dict with keys: url, title, text (up to 8000 chars), error (if any).
    """
    error = _validate_url(url)
    if error:
        logger.warning("url_reader_blocked", url=url[:80], reason=error)
        return {"url": url, "title": "", "text": "", "error": error}

    try:
        with httpx.Client(
            timeout=settings.request_timeout_seconds,
            follow_redirects=False,  # manual redirect handling to prevent SSRF via redirect
            headers={"User-Agent": "Mozilla/5.0 (compatible; Critique/1.0)"},
        ) as client:
            response = client.get(url)

            # Follow redirects manually, validating each hop
            hops = 0
            while response.is_redirect and hops < 5:
                redirect_url = response.headers.get("location", "")
                redirect_error = _validate_url(redirect_url)
                if redirect_error:
                    logger.warning(
                        "url_reader_redirect_blocked",
                        original_url=url[:80],
                        redirect_url=redirect_url[:80],
                        reason=redirect_error,
                    )
                    return {"url": url, "title": "", "text": "", "error": f"Redirect blocked: {redirect_error}"}
                response = client.get(redirect_url)
                hops += 1

            response.raise_for_status()

        # Reject non-HTML/text content types
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type and content_type not in _ALLOWED_CONTENT_TYPES:
            return {
                "url": url,
                "title": "",
                "text": "",
                "error": f"Unsupported content-type '{content_type}'",
            }

        # Guard against huge pages
        if len(response.content) > _MAX_RESPONSE_BYTES:
            return {
                "url": url,
                "title": "",
                "text": "",
                "error": f"Response too large ({len(response.content)} bytes)",
            }

        soup = BeautifulSoup(response.text, "lxml")

        # Remove noise tags
        for tag in soup(list(_REMOVE_TAGS)):
            tag.decompose()

        title = soup.title.string.strip() if soup.title else ""
        text = soup.get_text(separator=" ", strip=True)
        # Collapse excessive whitespace
        text = " ".join(text.split())

        logger.debug("url_reader_ok", url=url[:80], chars=len(text))
        return {"url": url, "title": title, "text": text[:_MAX_CHARS], "error": None}

    except Exception as exc:
        logger.warning("url_reader_failed", url=url[:80], error=str(exc))
        return {"url": url, "title": "", "text": "", "error": str(exc)}
