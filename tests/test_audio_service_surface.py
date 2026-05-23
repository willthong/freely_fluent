"""Test that AudioService has one responsibility — downloading audio.

Story 25: Remove dead `save_recording()`/`get_recording()` methods from
`AudioService`, so that the module has one responsibility — downloading
audio — and one method to learn.
"""

import httpx

from audio_service import AudioService


def test_audio_service_no_save_recording_method():
    """AudioService must not have a save_recording method.
    Recording management is the SessionManager's responsibility.
    """
    service = AudioService()
    assert not hasattr(service, "save_recording"), \
        "AudioService.save_recording() should be removed — dead code"
    service.close()


def test_audio_service_no_get_recording_method():
    """AudioService must not have a get_recording method.
    Recording management is the SessionManager's responsibility.
    """
    service = AudioService()
    assert not hasattr(service, "get_recording"), \
        "AudioService.get_recording() should be removed — dead code"
    service.close()


def test_audio_service_download_audio_still_works():
    """download_audio must still work with injected client."""
    audio_bytes = b"OggS\x00\x00\x00\x00mock audio data"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=audio_bytes)
    )
    client = httpx.Client(transport=transport)
    service = AudioService(client=client)
    result = service.download_audio("https://example.com/audio.ogg")
    assert result == audio_bytes
    service.close()


def test_audio_service_download_audio_failure_returns_none():
    """download_audio returns None on network failure."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(404)
    )
    client = httpx.Client(transport=transport)
    service = AudioService(client=client)
    result = service.download_audio("https://example.com/missing.ogg")
    assert result is None
    service.close()


def test_audio_service_close_cleanup():
    """close() must exist for client cleanup."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=b"data")
    )
    client = httpx.Client(transport=transport)
    service = AudioService(client=client)
    assert hasattr(service, "close")
    service.close()


def test_audio_service_public_methods():
    """Public API should be: download_audio, close — nothing more."""
    service = AudioService()
    public_methods = {m for m in dir(service) if not m.startswith("_")}
    assert "save_recording" not in public_methods
    assert "get_recording" not in public_methods
    assert "download_audio" in public_methods
    assert "close" in public_methods
    service.close()
