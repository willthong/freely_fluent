import httpx

from brave_image_search import BraveImageSearch


def _make_client(json_response: dict) -> httpx.Client:
    """Create an httpx client that returns the given JSON response."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=json_response)
    )
    return httpx.Client(transport=transport)


def test_search_returns_thumbnail_urls():
    """search returns thumbnail URLs for each result in a valid API response."""
    client = _make_client(
        {
            "results": [
                {
                    "type": "image_result",
                    "url": "https://example.com/page1",
                    "thumbnail": {
                        "src": "https://example.com/thumb1.jpg",
                        "width": 480,
                        "height": 360,
                    },
                    "properties": {
                        "url": "https://example.com/original1.jpg",
                    },
                },
                {
                    "type": "image_result",
                    "url": "https://example.com/page2",
                    "thumbnail": {
                        "src": "https://example.com/thumb2.jpg",
                        "width": 640,
                        "height": 480,
                    },
                    "properties": {
                        "url": "https://example.com/original2.jpg",
                    },
                },
            ]
        }
    )
    searcher = BraveImageSearch(api_key="mock-key", client=client)

    results = searcher.search("你好")

    assert len(results) == 2
    assert results[0]["thumbnail_url"] == "https://example.com/thumb1.jpg"
    assert results[0]["url"] == "https://example.com/original1.jpg"
    assert results[1]["thumbnail_url"] == "https://example.com/thumb2.jpg"
    assert results[1]["url"] == "https://example.com/original2.jpg"


def test_search_returns_empty_list_on_api_error():
    """search returns an empty list when the API returns an HTTP error."""
    transport = httpx.MockTransport(lambda request: httpx.Response(403))
    client = httpx.Client(transport=transport)
    searcher = BraveImageSearch(api_key="mock-key", client=client)

    results = searcher.search("你好")

    assert results == []


def test_search_returns_empty_list_when_no_results():
    """search returns an empty list when the API returns a valid response with no results."""
    client = _make_client({"results": []})
    searcher = BraveImageSearch(api_key="mock-key", client=client)

    results = searcher.search("不存在的字")

    assert results == []


def test_search_returns_empty_list_on_network_error():
    """search returns an empty list when the network call fails with an exception."""
    transport = httpx.MockTransport(
        lambda request: (_ for _ in ()).throw(httpx.ConnectError("connection refused"))
    )
    client = httpx.Client(transport=transport)
    searcher = BraveImageSearch(api_key="mock-key", client=client)

    results = searcher.search("你好")

    assert results == []


def test_search_passes_count_to_api():
    """search forwards count parameter to the API.

    Brave Image Search does NOT support offset-based pagination,
    so only count is passed.
    """
    captured_request = None

    def capture(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(200, json={"results": []})

    client = httpx.Client(transport=httpx.MockTransport(capture))
    searcher = BraveImageSearch(api_key="mock-key", client=client)
    searcher.search("你好", count=20)

    assert captured_request is not None
    params = dict(captured_request.url.params)
    assert params.get("q") == "你好"
    assert params.get("count") == "20"
    assert "offset" not in params
