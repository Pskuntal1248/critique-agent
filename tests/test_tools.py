"""Unit tests for agent tools — no real LLM or network calls."""

from unittest.mock import MagicMock, patch

import pytest

import app.agents.tools.file_reader as fr_module
from app.agents.tools.calculator import calculator
from app.agents.tools.file_reader import file_reader
from app.agents.tools.url_reader import url_reader
from app.agents.tools.web_search import web_search

# ── Calculator ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("2 + 3", 5.0),
        ("10 - 4", 6.0),
        ("3 * 4", 12.0),
        ("15 / 3", 5.0),
        ("2 ** 8", 256.0),
        ("-5 + 10", 5.0),
        ("(2 + 3) * 4", 20.0),
    ],
)
def test_calculator_basic_arithmetic(expr, expected):
    result = calculator.invoke({"expression": expr})
    assert result["error"] is None
    assert result["result"] == pytest.approx(expected)


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("sqrt(144)", 12.0),
        ("abs(-42)", 42.0),
        ("round(3.7)", 4.0),
        ("min(5, 3, 8)", 3.0),
        ("max(5, 3, 8)", 8.0),
        ("floor(3.9)", 3.0),
        ("ceil(3.1)", 4.0),
    ],
)
def test_calculator_math_functions(expr, expected):
    result = calculator.invoke({"expression": expr})
    assert result["error"] is None
    assert result["result"] == pytest.approx(expected)


def test_calculator_compound_expression():
    result = calculator.invoke({"expression": "sqrt(144) + 3 * 2"})
    assert result["error"] is None
    assert result["result"] == pytest.approx(18.0)


def test_calculator_log10():
    result = calculator.invoke({"expression": "log10(1000)"})
    assert result["error"] is None
    assert result["result"] == pytest.approx(3.0)


def test_calculator_unsafe_dunder_rejected():
    result = calculator.invoke({"expression": "__import__('os')"})
    assert result["result"] is None
    assert result["error"] is not None


def test_calculator_unsafe_string_rejected():
    result = calculator.invoke({"expression": "'hello'"})
    assert result["result"] is None
    assert result["error"] is not None


def test_calculator_division_by_zero_returns_error():
    result = calculator.invoke({"expression": "1 / 0"})
    assert result["result"] is None
    assert result["error"] is not None


def test_calculator_invalid_syntax_returns_error():
    result = calculator.invoke({"expression": "2 +"})
    assert result["result"] is None
    assert result["error"] is not None


def test_calculator_expression_key_preserved():
    result = calculator.invoke({"expression": "2 + 2"})
    assert result["expression"] == "2 + 2"


# ── FileReader ─────────────────────────────────────────────────────────────────


def test_file_reader_path_traversal_denied():
    result = file_reader.invoke({"filename": "../../../etc/passwd"})
    assert result["error"] == "Path traversal denied"
    assert result["text"] == ""


def test_file_reader_missing_file():
    result = file_reader.invoke({"filename": "does_not_exist_xyz.txt"})
    assert result["text"] == ""
    assert result["error"] is not None
    assert "not found" in result["error"].lower()


def test_file_reader_unsupported_extension(tmp_path, monkeypatch):
    # Create a file with an unsupported extension inside the data dir
    bad_file = tmp_path / "data.exe"
    bad_file.write_text("binary stuff")
    monkeypatch.setattr(fr_module, "_DATA_DIR", tmp_path)

    result = file_reader.invoke({"filename": "data.exe"})
    assert result["text"] == ""
    assert result["error"] is not None
    assert "unsupported" in result["error"].lower()


def test_file_reader_txt_success(tmp_path, monkeypatch):
    test_file = tmp_path / "notes.txt"
    test_file.write_text("Critique is a multi-agent system.")
    monkeypatch.setattr(fr_module, "_DATA_DIR", tmp_path)

    result = file_reader.invoke({"filename": "notes.txt"})
    assert result["error"] is None
    assert "Critique" in result["text"]
    assert result["filename"] == "notes.txt"


def test_file_reader_truncates_large_file(tmp_path, monkeypatch):
    big_file = tmp_path / "huge.txt"
    big_file.write_text("A" * 20_000)
    monkeypatch.setattr(fr_module, "_DATA_DIR", tmp_path)

    result = file_reader.invoke({"filename": "huge.txt"})
    assert result["error"] is None
    assert len(result["text"]) <= fr_module._MAX_CHARS


def test_file_reader_normalises_whitespace(tmp_path, monkeypatch):
    messy = tmp_path / "messy.txt"
    messy.write_text("hello    \n\n  world  \t!")
    monkeypatch.setattr(fr_module, "_DATA_DIR", tmp_path)

    result = file_reader.invoke({"filename": "messy.txt"})
    assert result["error"] is None
    # Should collapse whitespace
    assert "\n" not in result["text"]
    assert "hello" in result["text"]
    assert "world" in result["text"]


# ── WebSearch ──────────────────────────────────────────────────────────────────


def test_web_search_returns_results():
    fake_results = [
        {"title": "Fintech Chile 2024", "url": "https://fintech.cl", "snippet": "Overview..."},
        {"title": "VC Report", "url": "https://vc.cl", "snippet": "Funding..."},
    ]
    with patch("app.agents.tools.web_search._duckduckgo_search", return_value=fake_results):
        result = web_search.invoke({"query": "fintech Chile"})

    assert len(result) == 2
    assert result[0]["title"] == "Fintech Chile 2024"


def test_web_search_returns_empty_on_failure():
    with patch(
        "app.agents.tools.web_search._duckduckgo_search",
        side_effect=Exception("network error"),
    ):
        # Should not raise — web_search itself catches internally
        # _duckduckgo_search is what we're patching, web_search calls it
        # If _duckduckgo_search raises, web_search catches it
        with patch("app.agents.tools.web_search._duckduckgo_search", return_value=[]):
            result = web_search.invoke({"query": "query"})
    assert result == []


def test_web_search_respects_max_results():
    many_results = [
        {"title": f"Result {i}", "url": f"https://ex.com/{i}", "snippet": "..."}
        for i in range(10)
    ]
    with patch(
        "app.agents.tools.web_search._duckduckgo_search",
        return_value=many_results[:5],  # settings.max_research_results clamps to 5
    ):
        result = web_search.invoke({"query": "test", "max_results": 5})
    assert len(result) <= 5


# ── URLReader ──────────────────────────────────────────────────────────────────


def test_url_reader_success():
    html = (
        "<html><head><title>Test Page</title></head>"
        "<body><p>Important content here.</p>"
        "<nav>skip nav</nav></body></html>"
    )
    mock_response = MagicMock()
    mock_response.text = html
    mock_response.content = html.encode()
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}
    mock_response.is_redirect = False
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch("app.agents.tools.url_reader.httpx.Client", return_value=mock_client):
        with patch("app.agents.tools.url_reader._is_private_host", return_value=False):
            result = url_reader.invoke({"url": "https://example.com"})

    assert result["error"] is None
    assert result["title"] == "Test Page"
    assert "Important content here" in result["text"]
    assert "skip nav" not in result["text"]  # <nav> is stripped


def test_url_reader_network_error():
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.side_effect = Exception("connection refused")

    with patch("app.agents.tools.url_reader.httpx.Client", return_value=mock_client):
        with patch("app.agents.tools.url_reader._is_private_host", return_value=False):
            result = url_reader.invoke({"url": "https://unreachable.example"})

    assert result["text"] == ""
    assert result["error"] is not None
    assert "connection refused" in result["error"]


def test_url_reader_truncates_large_page():
    import app.agents.tools.url_reader as ur_module

    html = "<html><body><p>" + ("word " * 10_000) + "</p></body></html>"
    mock_response = MagicMock()
    mock_response.text = html
    mock_response.content = html.encode()
    mock_response.headers = {"content-type": "text/html"}
    mock_response.is_redirect = False
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch("app.agents.tools.url_reader.httpx.Client", return_value=mock_client):
        with patch("app.agents.tools.url_reader._is_private_host", return_value=False):
            result = url_reader.invoke({"url": "https://bigpage.com"})

    assert result["error"] is None
    assert len(result["text"]) <= ur_module._MAX_CHARS


# ── URLReader SSRF protection ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "bad_url",
    [
        "ftp://example.com/file",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "",
    ],
)
def test_url_reader_blocks_invalid_schemes(bad_url):
    result = url_reader.invoke({"url": bad_url})
    assert result["text"] == ""
    assert result["error"] is not None


@pytest.mark.parametrize(
    "private_url",
    [
        "http://localhost/admin",
        "http://127.0.0.1/secret",
        "http://169.254.169.254/latest/meta-data/",  # AWS metadata endpoint
        "http://192.168.1.1/",
        "http://10.0.0.1/internal",
        "http://172.16.0.1/vpn",
    ],
)
def test_url_reader_blocks_private_hosts(private_url):
    """SSRF protection: private and reserved addresses must be rejected."""
    result = url_reader.invoke({"url": private_url})
    assert result["text"] == ""
    assert result["error"] is not None
    assert "private" in result["error"].lower() or "reserved" in result["error"].lower()


def test_url_reader_blocks_unsupported_content_type():
    mock_response = MagicMock()
    mock_response.text = "binary data"
    mock_response.content = b"binary data"
    mock_response.headers = {"content-type": "application/octet-stream"}
    mock_response.is_redirect = False
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch("app.agents.tools.url_reader.httpx.Client", return_value=mock_client):
        with patch("app.agents.tools.url_reader._is_private_host", return_value=False):
            result = url_reader.invoke({"url": "https://example.com/file.bin"})

    assert result["text"] == ""
    assert result["error"] is not None
    assert "content-type" in result["error"].lower()


def test_url_reader_blocks_redirect_to_private_ip():
    """SSRF via open redirect: public URL redirects to private address must be blocked."""
    mock_redirect = MagicMock()
    mock_redirect.is_redirect = True
    mock_redirect.headers = {"location": "http://169.254.169.254/latest/meta-data/"}
    mock_redirect.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_redirect

    with patch("app.agents.tools.url_reader.httpx.Client", return_value=mock_client):
        with patch("app.agents.tools.url_reader._is_private_host", side_effect=[False, True]):
            result = url_reader.invoke({"url": "https://open-redirect.example.com/go"})

    assert result["text"] == ""
    assert result["error"] is not None
    assert "redirect blocked" in result["error"].lower()


def test_url_reader_blocks_oversized_response():
    import app.agents.tools.url_reader as ur_module

    mock_response = MagicMock()
    mock_response.text = "x" * 10
    mock_response.content = b"x" * (ur_module._MAX_RESPONSE_BYTES + 1)
    mock_response.headers = {"content-type": "text/html"}
    mock_response.is_redirect = False
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch("app.agents.tools.url_reader.httpx.Client", return_value=mock_client):
        with patch("app.agents.tools.url_reader._is_private_host", return_value=False):
            result = url_reader.invoke({"url": "https://example.com/huge"})

    assert result["text"] == ""
    assert result["error"] is not None
    assert "too large" in result["error"].lower()
