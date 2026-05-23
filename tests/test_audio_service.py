import httpx

from wiktionary_audio import fetch_audio_url
from audio_service import AudioService


def _make_httpx_client(fixture_name: str) -> httpx.Client:
    path = f"tests/fixtures/{fixture_name}"
    with open(path, "r", encoding="utf-8") as f:
        body = f.read().encode("utf-8")
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    return httpx.Client(transport=transport)


def test_download_audio_returns_bytes_from_url():
    """download_audio returns raw audio bytes from a working OGG URL."""
    audio_bytes = b"OggS\x00\x00\x00\x00mock audio data"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=audio_bytes)
    )
    service = AudioService(client=httpx.Client(transport=transport))

    result = service.download_audio("https://upload.wikimedia.org/wiki/Yue-nei5.ogg")

    assert result == audio_bytes


def test_download_audio_returns_none_on_http_error():
    """download_audio returns None when the server returns an error."""
    transport = httpx.MockTransport(lambda request: httpx.Response(404))
    service = AudioService(client=httpx.Client(transport=transport))

    result = service.download_audio("https://upload.wikimedia.org/wiki/missing.ogg")

    assert result is None


def test_full_flow_fetch_url_then_download():
    """fetch_audio_url + download_audio work end-to-end for a character with Cantonese audio."""
    wiktionary_client = _make_httpx_client("wiktionary_你.html")
    url = fetch_audio_url("你", wiktionary_client)
    assert url is not None

    audio_bytes = b"OggS\x00\x00mock yue audio"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=audio_bytes)
    )
    service = AudioService(client=httpx.Client(transport=transport))

    result = service.download_audio(url)
    assert result == audio_bytes


def test_download_audio_returns_none_on_request_error():
    """download_audio returns None on network/request errors."""
    transport = httpx.MockTransport(
        lambda request: (_ for _ in ()).throw(httpx.ReadError("connection reset"))
    )
    service = AudioService(client=httpx.Client(transport=transport))

    result = service.download_audio("https://upload.wikimedia.org/wiki/bad.ogg")
    assert result is None
    service.close()
