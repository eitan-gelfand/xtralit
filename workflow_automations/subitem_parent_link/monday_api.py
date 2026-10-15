"""Thin monday GraphQL helpers, called with the short-lived token monday sends us."""
import json

import requests

API_URL = "https://api.monday.com/v2"


def _run_query(token: str, query: str, variables: dict = None) -> dict:
    resp = requests.post(
        API_URL,
        json={"query": query, "variables": variables or {}},
        headers={"Authorization": token, "Content-Type": "application/json", "API-Version": "2024-10"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def create_subitem_webhook(token: str, board_id: str, url: str) -> str:
    """Register a create_subitem webhook on the parent board. Returns the webhook id."""
    query = """
    mutation ($boardId: ID!, $url: String!) {
      create_webhook(board_id: $boardId, url: $url, event: create_subitem) { id }
    }
    """
    return _run_query(token, query, {"boardId": board_id, "url": url})["create_webhook"]["id"]


def delete_app_subitem_webhooks(token: str, board_id: str) -> list[str]:
    """Delete this app's create_subitem webhooks on the board. Returns the deleted ids.

    Clears webhooks left behind by a subscribe call that failed after the webhook was
    created (monday never sends an unsubscribe for those, so they'd fire forever).
    """
    query = "query ($boardId: ID!) { webhooks(board_id: $boardId, app_webhooks_only: true) { id event } }"
    hooks = _run_query(token, query, {"boardId": board_id})["webhooks"] or []
    stale = [h["id"] for h in hooks if h["event"] == "create_subitem"]
    for webhook_id in stale:
        delete_webhook(token, webhook_id)
    return stale


def delete_webhook(token: str, webhook_id: str) -> None:
    query = "mutation ($id: ID!) { delete_webhook(id: $id) { id } }"
    _run_query(token, query, {"id": webhook_id})


def get_subitem(token: str, subitem_id: str) -> dict:
    """Fetch the subitem's board, its parent, and the subitems board's connect columns.

    The parent comes from monday itself rather than the webhook payload, so a forged
    call can't link a subitem to an arbitrary item.
    """
    query = """
    query ($id: [ID!]) {
      items(ids: $id) {
        id
        parent_item { id board { id } }
        board { id columns(types: [board_relation]) { id title settings_str } }
        column_values(types: [board_relation]) {
          id
          ... on BoardRelationValue { linked_item_ids }
        }
      }
    }
    """
    items = _run_query(token, query, {"id": [subitem_id]})["items"]
    return items[0] if items else None


def find_parent_connect_column(columns: list[dict], parent_board_id: str) -> dict | None:
    """The board_relation column on the subitems board that points at the parent board."""
    matches = []
    for col in columns:
        settings = json.loads(col.get("settings_str") or "{}")
        if str(parent_board_id) in [str(b) for b in settings.get("boardIds") or []]:
            matches.append(col)
    if len(matches) > 1:
        print(f"Several connect columns link to board {parent_board_id}; using {matches[0]['id']}", flush=True)
    return matches[0] if matches else None


def connect_items(token: str, board_id: str, item_id: str, column_id: str, linked_ids: list[str]) -> None:
    query = """
    mutation ($boardId: ID!, $itemId: ID!, $columnId: String!, $value: JSON!) {
      change_column_value(board_id: $boardId, item_id: $itemId, column_id: $columnId, value: $value) { id }
    }
    """
    value = json.dumps({"item_ids": [int(i) for i in linked_ids]})
    _run_query(token, query, {"boardId": board_id, "itemId": item_id, "columnId": column_id, "value": value})
