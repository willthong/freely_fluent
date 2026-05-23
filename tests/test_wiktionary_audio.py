import httpx

from wiktionary_audio import WiktionaryAudio, fetch_audio_url

FIXTURE_DIR = "tests/fixtures"


def _make_client(fixture_name: str) -> httpx.Client:
    """Create an httpx client that serves a recorded Wiktionary HTML fixture."""
    path = f"{FIXTURE_DIR}/{fixture_name}"
    with open(path, "r", encoding="utf-8") as f:
        body = f.read().encode("utf-8")

    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    return httpx.Client(transport=transport)


# ── fetch_html ──


def test_fetch_html_returns_raw_html():
    """WiktionaryAudio.fetch_html returns the raw HTML body for a character."""
    client = _make_client("wiktionary_你.html")
    service = WiktionaryAudio(client=client)

    html = service.fetch_html("你")

    assert html is not None
    assert "Wiktionary, the free dictionary" in html


def test_fetch_html_returns_none_on_http_error():
    """WiktionaryAudio.fetch_html returns None when the page returns a non-200."""
    transport = httpx.MockTransport(lambda request: httpx.Response(404))
    client = httpx.Client(transport=transport)
    service = WiktionaryAudio(client=client)

    html = service.fetch_html("不存在的字")

    assert html is None


def test_fetch_html_returns_none_on_request_error():
    """WiktionaryAudio.fetch_html returns None on network failure."""
    transport = httpx.MockTransport(lambda request: httpx.ConnectError("connection refused"))
    client = httpx.Client(transport=transport)
    service = WiktionaryAudio(client=client)

    html = service.fetch_html("你")

    assert html is None


# ── parse_html ──

CANTONESE_AUDIO_HTML = """
<html><body>
<dl><dd><span><audio data-mwtitle="zh-nǐ.ogg">
  <source src="//upload.wikimedia.org/7/73/Zh-nǐ.ogg" type="audio/ogg" />
  <source src="//upload.wikimedia.org/7/73/Zh-nǐ.ogg.mp3" type="audio/mpeg" />
</audio></span></dd></dl>
<dl><dd><span><audio data-mwtitle="yue-nei5.ogg">
  <source src="//upload.wikimedia.org/6/68/Yue-nei5.ogg" type="audio/ogg" />
  <source src="//upload.wikimedia.org/6/68/Yue-nei5.ogg.mp3" type="audio/mpeg" />
</audio></span></dd></dl>
</body></html>
"""


def test_parse_html_finds_cantonese_ogg_url():
    """WiktionaryAudio.parse_html extracts the Cantonese OGG URL from HTML."""
    service = WiktionaryAudio()

    url = service.parse_html(CANTONESE_AUDIO_HTML)

    assert url is not None
    assert "Yue-nei5.ogg" in url
    assert url.startswith("https://upload.wikimedia.org")


def test_parse_html_skips_mandarin_audio():
    """WiktionaryAudio.parse_html ignores Mandarin OGG (Zh- prefix) and returns Cantonese."""
    service = WiktionaryAudio()

    url = service.parse_html(CANTONESE_AUDIO_HTML)

    assert url is not None
    assert "Zh-" not in url


def test_parse_html_skips_ogg_mp3_transcode():
    """WiktionaryAudio.parse_html excludes .ogg.mp3 transcoded files."""
    service = WiktionaryAudio()

    url = service.parse_html(CANTONESE_AUDIO_HTML)

    assert url is not None
    assert ".ogg.mp3" not in url


def test_parse_html_returns_none_when_no_cantonese_audio():
    """WiktionaryAudio.parse_html returns None for HTML with no Cantonese audio."""
    mandarin_only_html = """
<html><body>
<dl><dd><span><audio data-mwtitle="zh-shān.ogg">
  <source src="//upload.wikimedia.org/c/cc/Zh-shān.ogg" type="audio/ogg" />
</audio></span></dd></dl>
</body></html>
"""
    service = WiktionaryAudio()

    url = service.parse_html(mandarin_only_html)

    assert url is None


def test_parse_html_finds_ll_q9186_recording():
    """WiktionaryAudio.parse_html matches LL-Q9186 Cantonese recordings."""
    ll_q9186_html = """
<html><body>
<dl><dd><span><audio data-mwtitle="LL-Q9186-Luilui6666-家庭.wav">
  <source src="//upload.wikimedia.org/transcoded/LL-Q9186-Luilui6666-家庭.wav/LL-Q9186-Luilui6666-家庭.wav.ogg" type="audio/ogg" />
  <source src="//upload.wikimedia.org/transcoded/LL-Q9186-Luilui6666-家庭.wav/LL-Q9186-Luilui6666-家庭.wav.mp3" type="audio/mpeg" />
</audio></span></dd></dl>
</body></html>
"""
    service = WiktionaryAudio()

    url = service.parse_html(ll_q9186_html)

    assert url is not None
    assert "LL-Q9186-" in url
    assert ".ogg" in url
    assert url.startswith("https://upload.wikimedia.org")


# ── fetch_audio_url (composed method) ──


def test_fetch_audio_url_method_chains_fetch_and_parse():
    """WiktionaryAudio.fetch_audio_url composes fetch_html and parse_html."""
    client = _make_client("wiktionary_你.html")
    service = WiktionaryAudio(client=client)

    url = service.fetch_audio_url("你")

    assert url is not None
    assert "Yue-nei5.ogg" in url


def test_fetch_audio_url_method_returns_none_on_parse_failure():
    """WiktionaryAudio.fetch_audio_url returns None when page has no Cantonese audio."""
    client = _make_client("wiktionary_山_audio.html")
    service = WiktionaryAudio(client=client)

    url = service.fetch_audio_url("山")

    assert url is None


def test_fetch_audio_url_method_returns_none_on_http_error():
    """WiktionaryAudio.fetch_audio_url returns None when the page fails to load."""
    transport = httpx.MockTransport(lambda request: httpx.Response(404))
    client = httpx.Client(transport=transport)
    service = WiktionaryAudio(client=client)

    url = service.fetch_audio_url("不存在的字")

    assert url is None


# ── backward-compatible fetch_audio_url() function ──


def test_backward_compat_fetch_audio_url_with_client():
    """fetch_audio_url() function delegates to WiktionaryAudio with injected client."""
    client = _make_client("wiktionary_你.html")

    url = fetch_audio_url("你", client=client)

    assert url is not None
    assert "Yue-nei5.ogg" in url


def test_backward_compat_fetch_audio_url_no_cantonese():
    """fetch_audio_url() function returns None for a character with no Cantonese audio."""
    client = _make_client("wiktionary_山_audio.html")

    url = fetch_audio_url("山", client=client)

    assert url is None


def test_backward_compat_fetch_audio_url_http_error():
    """fetch_audio_url() function returns None on HTTP error."""
    transport = httpx.MockTransport(lambda request: httpx.Response(404))
    client = httpx.Client(transport=transport)

    url = fetch_audio_url("不存在的字", client=client)

    assert url is None

