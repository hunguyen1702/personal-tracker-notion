import httpx
import pytest

from personal_tracker.notion.client import DatabaseClient, NotionAPIError


@pytest.fixture
def client(httpx_mock):
    http = httpx.Client(
        base_url="https://api.notion.com/v1",
        headers={"Authorization": "Bearer test", "Notion-Version": "2022-06-28"},
    )
    db = DatabaseClient(
        database_id="db-123",
        token="test",
        sleep_seconds=0,
        max_retries=3,
        http_client=http,
    )
    yield db
    db.close()


def test_retrieve_pages_paginates(client, httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.notion.com/v1/databases/db-123/query",
        json={
            "results": [{"id": "p1", "properties": {}}],
            "has_more": True,
            "next_cursor": "cur1",
        },
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.notion.com/v1/databases/db-123/query",
        json={"results": [{"id": "p2", "properties": {}}], "has_more": False},
    )

    pages = client.retrieve_pages(filter={"and": []})
    assert [p["id"] for p in pages] == ["p1", "p2"]


def test_retrieve_pages_filters_formula_properties(client, httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.notion.com/v1/databases/db-123/query",
        json={
            "results": [
                {
                    "id": "p1",
                    "properties": {
                        "Name": {"type": "title", "title": []},
                        "Computed": {"type": "formula", "formula": {}},
                    },
                }
            ],
            "has_more": False,
        },
    )
    pages = client.retrieve_pages()
    assert "Computed" not in pages[0]["properties"]
    assert "Name" in pages[0]["properties"]


def test_retry_on_429(client, httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.notion.com/v1/databases/db-123/query",
        status_code=429,
        text="rate limited",
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.notion.com/v1/databases/db-123/query",
        json={"results": [], "has_more": False},
    )
    assert client.retrieve_pages() == []


def test_retry_exhausted_raises(client, httpx_mock):
    for _ in range(3):
        httpx_mock.add_response(
            method="POST",
            url="https://api.notion.com/v1/databases/db-123/query",
            status_code=500,
            text="server boom",
        )
    with pytest.raises(NotionAPIError):
        client.retrieve_pages()


def test_update_page(client, httpx_mock):
    httpx_mock.add_response(
        method="PATCH",
        url="https://api.notion.com/v1/pages/page-1",
        json={"object": "page", "id": "page-1"},
    )
    assert client.update_page("page-1", {"Name": {"type": "title", "title": []}}) is True


def test_create_page(client, httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.notion.com/v1/pages",
        json={"object": "page", "id": "new-page"},
    )
    result = client.create_page({"Name": {"type": "title", "title": []}})
    assert result["id"] == "new-page"
    sent = httpx_mock.get_request()
    assert sent.method == "POST"
    body = sent.read().decode()
    assert "db-123" in body
    assert "Name" in body


def test_retrieve_page_strips_formula(client, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url="https://api.notion.com/v1/pages/page-x",
        json={
            "id": "page-x",
            "properties": {
                "Name": {"type": "title", "title": []},
                "Computed": {"type": "formula", "formula": {}},
            },
        },
    )
    page = client.retrieve_page("page-x")
    assert page["id"] == "page-x"
    assert "Computed" not in page["properties"]
    assert "Name" in page["properties"]


def test_add_comment(client, httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.notion.com/v1/comments",
        json={"object": "comment", "id": "c-1"},
    )
    assert client.add_comment("page-1", "hello") is True


def test_create_page_with_children_and_icon(client, httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.notion.com/v1/pages",
        json={"object": "page", "id": "new-page"},
    )
    children = [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}]
    icon = {"type": "emoji", "emoji": "🎯"}
    client.create_page(
        {"Name": {"type": "title", "title": []}},
        children=children,
        icon=icon,
    )
    body = httpx_mock.get_request().read().decode()
    assert '"children"' in body
    assert '"icon"' in body
    assert "🎯" in body


def test_create_page_omits_optional_fields(client, httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.notion.com/v1/pages",
        json={"object": "page", "id": "new-page"},
    )
    client.create_page({"Name": {"type": "title", "title": []}})
    body = httpx_mock.get_request().read().decode()
    assert '"children"' not in body
    assert '"icon"' not in body


def test_update_page_with_icon_sends_patch(client, httpx_mock):
    httpx_mock.add_response(
        method="PATCH",
        url="https://api.notion.com/v1/pages/page-1",
        json={"object": "page", "id": "page-1"},
    )
    client.update_page("page-1", icon={"type": "emoji", "emoji": "🚀"})
    body = httpx_mock.get_request().read().decode()
    assert '"properties"' not in body
    assert '"icon"' in body
    assert "🚀" in body


def test_update_page_clear_icon_sends_null(client, httpx_mock):
    httpx_mock.add_response(
        method="PATCH",
        url="https://api.notion.com/v1/pages/page-1",
        json={"object": "page", "id": "page-1"},
    )
    client.update_page("page-1", icon=None)
    body = httpx_mock.get_request().read().decode()
    assert '"icon":null' in body


def test_update_page_default_icon_omits_icon_field(client, httpx_mock):
    httpx_mock.add_response(
        method="PATCH",
        url="https://api.notion.com/v1/pages/page-1",
        json={"object": "page", "id": "page-1"},
    )
    client.update_page("page-1", {"Name": {"type": "title", "title": []}})
    body = httpx_mock.get_request().read().decode()
    assert '"properties"' in body
    assert '"icon"' not in body


def test_update_page_default_icon_and_no_properties_noop(client, httpx_mock):
    assert client.update_page("page-1") is True
    assert len(httpx_mock.get_requests()) == 0


def test_append_block_children(client, httpx_mock):
    httpx_mock.add_response(
        method="PATCH",
        url="https://api.notion.com/v1/blocks/page-1/children",
        json={"object": "list", "results": []},
    )
    blocks = [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}]
    result = client.append_block_children("page-1", blocks)
    assert result["object"] == "list"
    body = httpx_mock.get_request().read().decode()
    assert '"children"' in body
