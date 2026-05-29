"""Unit tests for SessionManager.

Story 21: SessionManager accepts CardStore, completes save-advance.
Story 22: Add unit tests for session_manager.py covering pipeline state,
advancement, skip, load_more_images, recording, and card data building.
"""

import tempfile

import pytest

from card_store import CardStore, CardStoreProtocol, Flashcard
from session_manager import SessionManager


def test_init_sets_translate_step():
    """Fresh session starts at translate step."""
    sm = SessionManager(["hello", "goodbye"])
    assert sm.current_step == "translate"
    assert sm.current_word == "hello"


def test_is_complete_false_on_start():
    """Session is not complete when just started."""
    sm = SessionManager(["hello"])
    assert not sm.is_complete


def test_is_complete_true_after_all_words_processed():
    """Session becomes complete after advancing past all words."""
    sm = SessionManager(["hello"])
    sm.skip()
    assert sm.is_complete


def test_current_word_is_none_when_complete():
    """current_word returns None after session is complete."""
    sm = SessionManager(["hello"])
    sm.skip()
    assert sm.current_word is None


def test_select_entry_advances_to_image_step():
    """select_entry records entry and moves to image step."""
    sm = SessionManager(["hello"])
    entry = {"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"}
    sm.select_entry(entry)
    assert sm.current_step == "image"
    assert sm.selected_characters == "\u4f60\u597d"
    assert sm.selected_entry == entry


def test_add_image_advances_to_audio_step():
    """Adding an image advances to audio step."""
    sm = SessionManager(["hello"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    assert sm.current_step == "audio"
    assert len(sm.selected_images) == 1


def test_add_multiple_images():
    """Multiple images accumulate."""
    sm = SessionManager(["hello"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img1.jpg"})
    sm.add_image({"thumbnail_url": "https://example.com/img2.jpg"})
    assert len(sm.selected_images) == 2


def test_select_audio_returns_card_data():
    """select_audio returns card data dict when all fields present."""
    sm = SessionManager(["hello"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    audio = b"OggS"
    card = sm.select_audio(audio)
    assert card is not None
    assert card["english_word"] == "hello"
    assert card["chinese_characters"] == "\u4f60\u597d"
    assert card["jyutping"] == "nei5 hou2"
    assert card["audio"] == audio


def test_select_audio_advances_to_next_word():
    """select_audio advances to next word after building card."""
    sm = SessionManager(["hello", "goodbye"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    sm.select_audio(b"OggS")
    assert sm.current_word == "goodbye"
    assert sm.current_step == "translate"


def test_select_audio_returns_none_missing_entry():
    """select_audio returns None if no entry selected."""
    sm = SessionManager(["hello"])
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    card = sm.select_audio(b"OggS")
    assert card is None


def test_select_audio_returns_none_missing_images():
    """select_audio returns None if no images selected."""
    sm = SessionManager(["hello"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    card = sm.select_audio(b"OggS")
    assert card is None


def test_select_audio_returns_none_missing_audio():
    """select_audio returns None if no audio (downloaded or recorded)."""
    sm = SessionManager(["hello"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    card = sm.select_audio(None)
    assert card is None


def test_select_audio_uses_recording_when_download_fails():
    """select_audio falls back to recording if download returns None."""
    sm = SessionManager(["hello"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    sm.save_recording(b"\x00\x01webm data")
    card = sm.select_audio(None)
    assert card is not None
    assert card["audio"] == b"\x00\x01webm data"


def test_save_and_get_recording():
    """Browser recording can be saved and retrieved."""
    sm = SessionManager(["hello"])
    data = b"\x00\x01webm data"
    sm.save_recording(data)
    assert sm.get_recording() == data


def test_get_recording_returns_none_by_default():
    """get_recording returns None if no recording saved."""
    sm = SessionManager(["hello"])
    assert sm.get_recording() is None


def test_skip_advances_to_next_word():
    """skip discards current word and moves to next."""
    sm = SessionManager(["hello", "goodbye"])
    sm.skip()
    assert sm.current_word == "goodbye"
    assert sm.current_step == "translate"


def test_skip_resets_selections():
    """skip resets all selections for the new word."""
    sm = SessionManager(["hello", "goodbye"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    sm.save_recording(b"webm data")
    sm.skip()
    assert sm.selected_entry is None
    assert sm.selected_characters is None
    assert len(sm.selected_images) == 0
    assert sm.selected_audio is None
    assert sm.get_recording() is None
    assert sm.image_offset == 0


def test_load_more_images_advances_offset():
    """load_more_images increments offset by batch_size."""
    sm = SessionManager(["hello"])
    new_offset = sm.load_more_images(12)
    assert new_offset == 12
    assert sm.image_offset == 12
    new_offset = sm.load_more_images()
    assert new_offset == 24


def test_load_more_images_returns_offset():
    """load_more_images returns the new offset value."""
    sm = SessionManager(["hello"])
    assert sm.load_more_images(10) == 10


def test_full_pipeline_two_words():
    """Complete pipeline for two words in sequence."""
    sm = SessionManager(["hello", "goodbye"])

    # Process word 1
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG1"})
    card1 = sm.select_audio(b"OggS")
    assert card1 is not None
    assert card1["english_word"] == "hello"
    assert sm.current_word == "goodbye"

    # Process word 2
    sm.select_entry({"chinese": "\u518d\u89c1", "jyutping": "zaai6 gin3"})
    sm.add_image({"thumbnail_url": b"\x89PNG2"})
    card2 = sm.select_audio(b"OggS2")
    assert card2 is not None
    assert card2["english_word"] == "goodbye"
    assert sm.is_complete


def test_image_offset_resets_on_advance():
    """image_offset resets when advancing to next word."""
    sm = SessionManager(["hello", "goodbye"])
    sm.load_more_images(12)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    sm.select_audio(b"OggS")
    assert sm.image_offset == 0


def test_steps_constant():
    """STEPS constant defines the pipeline order."""
    assert SessionManager.STEPS == ("translate", "image", "audio")


def test_step_progression():
    """Step advances through translate -> image -> audio."""
    sm = SessionManager(["hello"])
    assert sm.current_step == "translate"
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    assert sm.current_step == "image"
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    assert sm.current_step == "audio"


def test_empty_words_list():
    """Session with empty words list is immediately complete."""
    sm = SessionManager([])
    assert sm.is_complete
    assert sm.current_word is None


def test_single_word_complete_after_skip():
    """Single word session becomes complete after skip."""
    sm = SessionManager(["hello"])
    sm.skip()
    assert sm.is_complete

# ── Brave redirect URL decoding ──────────────────────────────────────


def test_decode_brave_redirect_known_url():
    """_decode_brave_redirect_url decodes a known Brave redirect to original URL."""
    sm = SessionManager(["hello"])
    brave_url = ("https://imgs.search.brave.com/abc123/rs:fit:500:0:1:0/g:ce/"
                 "aHR0cHM6Ly9leGFtcGxlLmNvbS9pbWFnZS5qcGc")
    result = sm._decode_brave_redirect_url(brave_url)
    assert result == "https://example.com/image.jpg"


def test_decode_brave_redirect_non_brave_url():
    """_decode_brave_redirect_url returns None for non-Brave URLs."""
    sm = SessionManager(["hello"])
    result = sm._decode_brave_redirect_url("https://example.com/image.jpg")
    assert result is None


def test_decode_brave_redirect_empty_string():
    """_decode_brave_redirect_url returns None for empty string."""
    sm = SessionManager(["hello"])
    result = sm._decode_brave_redirect_url("")
    assert result is None


def test_decode_brave_redirect_malformed_url():
    """_decode_brave_redirect_url returns None for malformed Brave URL (no g:ce/)."""
    sm = SessionManager(["hello"])
    result = sm._decode_brave_redirect_url("https://imgs.search.brave.com/abc123/not-a-valid-url")
    assert result is None


def test_decode_brave_redirect_real_world_example():
    """_decode_brave_redirect_url decodes a real-world ClubBBoss URL."""
    sm = SessionManager(["hello"])
    url = ("https://imgs.search.brave.com/DklKwsoe8KVaTIQTo583rrVT6uHxO9saZR4GCyyqSwk/"
           "rs:fit:500:0:1:0/g:ce/"
           "aHR0cHM6Ly93d3cub3VyY2hpbmFzdG9yeS5jb20vaW1hZ2VzL2NvdmVyL2hvbmgra29uZy8yMDI1LzA2L3NxdWFyZS9DbHViQkJvc3NfeDEuanBn")
    assert sm._decode_brave_redirect_url(url) == "https://www.ourchinastory.com/images/cover/honh+kong/2025/06/square/ClubBBoss_x1.jpg"


# ── Image resolution: Brave redirect fallback chain ───────────────────


def test_resolve_image_brave_redirect_original_succeeds():
    """Brave redirect: decoded original URL downloads successfully → return its bytes."""
    from unittest.mock import Mock
    sm = SessionManager(["hello"])
    brave_url = ("https://imgs.search.brave.com/abc123/rs:fit:500:0:1:0/g:ce/"
                 "aHR0cHM6Ly9leGFtcGxlLmNvbS9pbWFnZS5qcGc")
    sm._http_client = Mock()
    sm._http_client.get = Mock(
        return_value=Mock(status_code=200, content=b"ORIGINAL_BYTES")
    )
    result = sm._resolve_image(brave_url)
    assert result == b"ORIGINAL_BYTES"
    # Only one download attempt (original succeeded)
    assert sm._http_client.get.call_count == 1


def test_resolve_image_brave_redirect_original_fails_proxy_succeeds():
    """Brave redirect: original returns 403, proxy succeeds → return proxy bytes."""
    from unittest.mock import Mock
    sm = SessionManager(["hello"])
    original_url = "https://example.com/image.jpg"
    brave_url = ("https://imgs.search.brave.com/abc123/rs:fit:500:0:1:0/g:ce/"
                 "aHR0cHM6Ly9leGFtcGxlLmNvbS9pbWFnZS5qcGc")
    sm._http_client = Mock()
    def get_side_effect(url, **kw):
        if url == original_url:
            return Mock(status_code=403, content=b"Forbidden")
        elif url == brave_url:
            return Mock(status_code=200, content=b"PROXY_BYTES")
        return Mock(status_code=404)
    sm._http_client.get = Mock(side_effect=get_side_effect)
    result = sm._resolve_image(brave_url)
    assert result == b"PROXY_BYTES"
    # Both URLs were tried
    assert sm._http_client.get.call_count == 2


def test_resolve_image_brave_redirect_both_fail():
    """Brave redirect: both original and proxy return 403 → return None."""
    from unittest.mock import Mock
    sm = SessionManager(["hello"])
    brave_url = ("https://imgs.search.brave.com/abc123/rs:fit:500:0:1:0/g:ce/"
                 "aHR0cHM6Ly9leGFtcGxlLmNvbS9pbWFnZS5qcGc")
    sm._http_client = Mock()
    sm._http_client.get = Mock(
        return_value=Mock(status_code=403, content=b"Forbidden")
    )
    result = sm._resolve_image(brave_url)
    assert result is None
    # Both URLs were tried
    assert sm._http_client.get.call_count == 2


def test_resolve_image_brave_redirect_request_error():
    """Brave redirect: RequestError on both URLs → return None."""
    import httpx
    from unittest.mock import Mock
    sm = SessionManager(["hello"])
    sm._http_client = Mock()
    sm._http_client.get = Mock(side_effect=httpx.RequestError("Connection error"))
    brave_url = ("https://imgs.search.brave.com/abc123/rs:fit:500:0:1:0/g:ce/"
                 "aHR0cHM6Ly9leGFtcGxlLmNvbS9pbWFnZS5qcGc")
    result = sm._resolve_image(brave_url)
    assert result is None


# ── Image resolution: URL strings must not be saved as image_data ──


def _mock_http_client(status_code=200, content=b"\x89PNG fake image"):
    """Build a fake httpx client for testing._http_client."""
    import httpx
    response = httpx.Response(
        status_code=status_code,
        content=content,
        headers={"Content-Type": "image/png"},
        request=httpx.Request("GET", "https://example.com/img.jpg"),
    )
    fake = httpx.Client()
    fake.get = lambda *args, **kwargs: response
    return fake


def test_select_audio_download_403_no_save():
    """When the HTTP client returns 403, image can't be resolved.
    select_audio returns None and does NOT advance."""
    import httpx
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm._http_client = _mock_http_client(status_code=403)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    result = sm.select_audio(b"OggS")
    assert result is None
    assert sm.current_word == "hello"  # no advance
    assert len(store.get_all()) == 0


def test_select_audio_download_200_saves_real_bytes():
    """When the HTTP client returns 200, image bytes are saved to Flashcard."""
    import httpx
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    real_image = b"\x89PNG\r\n\x1a\n real image data here"
    sm._http_client = _mock_http_client(status_code=200, content=real_image)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    result = sm.select_audio(b"OggS")
    assert result is not None
    assert result.image_data == [real_image]
    assert sm.current_word is None  # only word, now complete
    assert len(store.get_all()) == 1


def test_select_audio_request_error_no_save():
    """When httpx raises RequestError, image can't be resolved.
    select_audio returns None and does NOT advance."""
    import httpx
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)

    class _broken_client(httpx.Client):
        def get(self, *a, **kw):
            raise httpx.ConnectError("DNS failure")

    sm._http_client = _broken_client()
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    result = sm.select_audio(b"OggS")
    assert result is None
    assert sm.current_word == "hello"  # no advance
    assert len(store.get_all()) == 0


def test_select_audio_no_advance_when_image_url_cannot_resolve():
    """When image is a URL string and no HTTP client is injected,
    select_audio returns None and does NOT advance the session.
    The URL was never real image data — saving it would produce a broken card."""
    sm = SessionManager(["hello"], card_store=_make_store())
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    result = sm.select_audio(b"OggS")
    # Must not save a broken card or lose session state
    assert result is None
    assert sm.current_word == "hello"  # still on same word — no advance
    assert len(sm._card_store.get_all()) == 0  # nothing saved


def test_select_audio_no_advance_backward_compat_no_store():
    """Without card_store + unresolved image URL, select_audio returns None
    and does NOT advance session. (Old behavior returned a dict with URL-as-bytes)."""
    sm = SessionManager(["hello"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    result = sm.select_audio(b"OggS")
    assert result is None
    assert sm.current_word == "hello"  # no advance


# ── Story 21: CardStore injection & save-advance ─────────────────────────


def _make_store() -> CardStore:
    """Create a fresh CardStore backed by a temp file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return CardStore(tmp.name)


def test_construction_with_card_store():
    """SessionManager accepts a CardStoreProtocol at construction."""
    sm = SessionManager(["hello"], card_store=_make_store())
    assert sm.current_word == "hello"


def test_select_audio_saves_via_card_store():
    """When card_store is injected, select_audio saves the Flashcard."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG real image data"})
    result = sm.select_audio(b"OggS")
    # Should return the saved Flashcard (not a dict)
    from card_store import Flashcard
    assert isinstance(result, Flashcard)
    assert result.id is not None
    # Verify it was actually persisted
    retrieved = store.get_flashcard(result.id)
    assert retrieved is not None
    assert retrieved.english_word == "hello"
    assert retrieved.chinese_characters == "\u4f60\u597d"
    assert retrieved.jyutping == "nei5 hou2"
    assert retrieved.audio_data == b"OggS"
    # image_data must be real bytes, not a URL string
    assert b"\x89PNG" in retrieved.image_data[0]


def test_select_audio_saves_image_data_from_first_image():
    """Saved Flashcard image_data includes all selected images."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG first image"})
    sm.add_image({"thumbnail_url": b"\x89PNG second image"})
    result = sm.select_audio(b"OggS")
    assert result is not None
    assert result.image_data == [b"\x89PNG first image", b"\x89PNG second image"]


def test_select_audio_no_save_when_fields_missing():
    """When fields are missing, select_audio returns None and does not save."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    # No entry selected — missing required field
    result = sm.select_audio(b"OggS")
    assert result is None
    assert len(store.get_all()) == 0


def test_select_audio_advances_after_save():
    """After saving, session advances to next word."""
    store = _make_store()
    sm = SessionManager(["hello", "goodbye"], card_store=store)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    sm.select_audio(b"OggS")
    assert sm.current_word == "goodbye"
    assert sm.current_step == "translate"


def test_select_audio_backward_compat_no_store():
    """Without card_store, select_audio returns card_data dict."""
    sm = SessionManager(["hello"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")
    assert isinstance(result, dict)
    assert result["english_word"] == "hello"


def test_select_audio_backward_compat_no_store_returns_none_when_incomplete():
    """Without card_store, still returns None when fields missing."""
    sm = SessionManager(["hello"])
    result = sm.select_audio(b"OggS")
    assert result is None


def test_full_pipeline_two_words_with_store():
    """Complete pipeline for two words, both saved to CardStore."""
    store = _make_store()
    sm = SessionManager(["hello", "goodbye"], card_store=store)

    # Word 1
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG img1"})
    card1 = sm.select_audio(b"OggS")
    assert card1 is not None
    assert card1.english_word == "hello"

    # Word 2
    sm.select_entry({"chinese": "\u518d\u89c1", "jyutping": "zaai6 gin3"})
    sm.add_image({"thumbnail_url": b"\x89PNG img2"})
    card2 = sm.select_audio(b"OggS2")
    assert card2 is not None
    assert card2.english_word == "goodbye"

    assert sm.is_complete
    assert len(store.get_all()) == 2
    assert store.get_all()[0].english_word == "hello"
    assert store.get_all()[1].english_word == "goodbye"


def test_select_audio_falls_back_to_recording_with_store():
    """When download returns None but recording exists, save from recording."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    sm.save_recording(b"\x00\x01webm data")
    result = sm.select_audio(None)
    assert result is not None
    assert result.audio_data == b"\x00\x01webm data"


def test_select_audio_no_recording_no_save():
    """When no download and no recording, does not save."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(None)
    assert result is None
    assert len(store.get_all()) == 0


# ── Session ID propagation ──


def test_select_audio_passes_session_id_to_flashcard():
    """When SessionManager has a session_id, the saved Flashcard carries it."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm._session_id = "sess-abc-123"
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")
    assert result is not None
    assert result.session_id == "sess-abc-123"
    # Also check it's in the store
    retrieved = store.get_by_session("sess-abc-123")
    assert len(retrieved) == 1
    assert retrieved[0].english_word == "hello"


def test_select_audio_no_session_id_defaults_empty():
    """Without _session_id set, the Flashcard gets an empty session_id."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")
    assert result is not None
    assert result.session_id == ""


def test_two_words_different_sessions_not_deduped():
    """Same word in different sessions should still deduplicate within
    the same uniqueness key, but get_by_session separates them correctly."""
    store = _make_store()
    sm1 = SessionManager(["hello"], card_store=store)
    sm1._session_id = "sess-1"
    sm1.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm1.add_image({"thumbnail_url": b"\x89PNG img1"})
    sm1.select_audio(b"ogg1")

    # Second session saves same word — UPSERT will overwrite, but
    # session_id also updates (that's the UPSERT semantics)
    sm2 = SessionManager(["hello"], card_store=store)
    sm2._session_id = "sess-2"
    sm2.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm2.add_image({"thumbnail_url": b"\x89PNG img2"})
    sm2.select_audio(b"ogg2")

    # After UPSERT, only one row exists (with sess-2's data)
    assert len(store.get_all()) == 1
    cards_s1 = store.get_by_session("sess-1")
    cards_s2 = store.get_by_session("sess-2")
    assert len(cards_s1) == 0
    assert len(cards_s2) == 1
    assert cards_s2[0].image_data == [b"\x89PNG img2"]


def test_e2e_multiple_images_round_trip():
    """Full pipeline: add multiple images, save to store, retrieve,
    generate apkg, verify images appear in card fields."""
    import zipfile as zf
    import sqlite3

    from card_generator import CardGenerator

    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": b"\x89PNG\r\n\x1a\n image1 data"})
    sm.add_image({"thumbnail_url": b"\xff\xd8\xff\xe0 image2 data"})
    sm.add_image({"thumbnail_url": b"\x89PNG\r\n\x1a\n image3 data"})
    sm.select_audio(b"OggS audio data")

    # Verify stored card has all 3 images
    cards = store.get_all()
    assert len(cards) == 1
    assert len(cards[0].image_data) == 3

    # Generate apkg from the stored cards
    generator = CardGenerator()
    tmp = tempfile.NamedTemporaryFile(suffix=".apkg", delete=False)
    path = tmp.name
    count = generator.generate_apkg(cards, path)
    assert count == 2  # reversed pair

    # Verify images appear in card fields
    with zf.ZipFile(path, "r") as z:
        db_path = z.extract("collection.anki2", tempfile.mkdtemp())
        conn = sqlite3.connect(db_path)
        notes = conn.execute("SELECT flds FROM notes").fetchone()
        fields = notes[0].split("\x1f")
        combined = " ".join(fields)
        img_count = combined.count("<img src=")
        assert img_count >= 3, f"Expected 3 img tags, got {img_count}"
        conn.close()


# ── Export route scoping (integration) ──


def _mock_cantodict():
    from unittest.mock import Mock
    from cantodict_lookup import CantoneseDictionary
    m = Mock(spec=CantoneseDictionary)
    m.lookup = Mock(return_value=[{"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"}])
    return m


def test_export_with_session_id_returns_only_session_cards():
    """GET /export?session_id=X uses get_by_session, not get_all."""
    from unittest.mock import Mock
    from fastapi.testclient import TestClient
    from app import create_app

    store = _make_store()
    cantodict = _mock_cantodict()
    card_gen = Mock()
    card_gen.generate_apkg = Mock()
    app = create_app(cantodict=cantodict, card_store=store, card_generator=card_gen)
    client = TestClient(app)

    # Create session-1 with "hello"
    resp = client.post("/sessions", json={"words": ["hello"]})
    sid1 = resp.json()["session_id"]
    client.post(f"/sessions/{sid1}/entries", json={"chinese": "\u4f60\u597d"})
    # Add image (we need a valid index, but the mock won't return results;
    # so we use the raw store to place cards directly)
    store.save_flashcard(
        Flashcard(
            english_word="hello", chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2", image_data=[b"\x89PNG"], audio_data=b"ogg1",
            session_id=sid1,
        )
    )

    # Create session-2 with "goodbye"
    resp = client.post("/sessions", json={"words": ["goodbye"]})
    sid2 = resp.json()["session_id"]
    store.save_flashcard(
        Flashcard(
            english_word="goodbye", chinese_characters="\u518d\u89c1",
            jyutping="zaai6 gin3", image_data=[b"\x89PNG2"], audio_data=b"ogg2",
            session_id=sid2,
        )
    )

    # Export with session_id=sid1 should only return cards from sess-1
    export_resp = client.get(f"/export?session_id={sid1}")
    assert export_resp.status_code == 200
    # Verify generate_apkg was called with only session-1 cards
    call_args = card_gen.generate_apkg.call_args
    assert len(call_args[0][0]) == 1  # 1 flashcard in the list
    assert call_args[0][0][0].english_word == "hello"

    # Reset mock for next call
    card_gen.generate_apkg.reset_mock()

    # Export without session_id returns all
    export_all = client.get("/export")
    assert export_all.status_code == 200
    call_args = card_gen.generate_apkg.call_args
    assert len(call_args[0][0]) == 2  # both flashcards

    # Verify: get_by_session gives correct subset
    assert len(store.get_by_session(sid1)) == 1
    assert store.get_by_session(sid1)[0].english_word == "hello"
    assert len(store.get_by_session(sid2)) == 1
    assert store.get_by_session(sid2)[0].english_word == "goodbye"


def test_completion_passes_session_id_to_export():
    """Completion page includes session_id in the export link."""
    from fastapi.testclient import TestClient
    from app import create_app

    store = _make_store()
    cantodict = _mock_cantodict()
    app = create_app(cantodict=cantodict, card_store=store)
    client = TestClient(app)

    resp = client.post("/sessions", json={"words": ["hello"]})
    sid = resp.json()["session_id"]

    # Place a card in the store with this session_id
    store.save_flashcard(
        Flashcard(
            english_word="hello", chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2", image_data=[b"\x89PNG"], audio_data=b"ogg",
            session_id=sid,
        )
    )

    complete_resp = client.get(f"/complete/{sid}")
    assert complete_resp.status_code == 200
    html = complete_resp.text
    # Export link should contain the session_id
    assert "export" in html
    assert sid in html
