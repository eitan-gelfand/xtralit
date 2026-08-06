"""Standalone monday.com connector: list Active Requests items, fetch fresh fields.

Run directly for the Step 2 checkpoint: prints current Active Requests items to
the terminal.
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.monday.com/v2"
API_TOKEN = os.environ.get("MONDAY_API_TOKEN")
BOARD_ID = os.environ.get("BOARD_ID")
GROUP_ID = os.environ.get("GROUP_ID")
NAME_COLUMN_ID = os.environ.get("NAME_COLUMN_ID")  # unused: item name is the built-in "name" field
NUMBER_COLUMN_ID = os.environ.get("NUMBER_COLUMN_ID")  # "N of samples" - numeric_mknnwms1
ADD_SAMPLES_COLUMN_ID = os.environ.get("ADD_SAMPLES_COLUMN_ID")  # "Add. samples" - dropdown_mkp0kky2
DATE_COLUMN_ID = os.environ.get("DATE_COLUMN_ID", "date4")  # "Date"


def _run_query(query: str, variables: dict = None) -> dict:
    if not API_TOKEN:
        raise ValueError("MONDAY_API_TOKEN not set")
    resp = requests.post(
        API_URL,
        json={"query": query, "variables": variables or {}},
        headers={"Authorization": API_TOKEN, "Content-Type": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def list_active_requests_items(board_id: str = None, group_id: str = None) -> list[dict]:
    """List items in the Active Requests group. Returns [{id, name}]."""
    board_id = board_id or BOARD_ID
    group_id = group_id or GROUP_ID
    query = """
    query ($boardId: [ID!], $groupId: [String!]) {
      boards(ids: $boardId) {
        groups(ids: $groupId) {
          items_page(limit: 100) {
            items { id name }
          }
        }
      }
    }
    """
    data = _run_query(query, {"boardId": [board_id], "groupId": [group_id]})
    boards = data.get("boards") or []
    if not boards or not boards[0]["groups"]:
        return []
    return boards[0]["groups"][0]["items_page"]["items"]


def get_item_fields(item_id: str, number_column_id: str = None, add_samples_column_id: str = None,
                     date_column_id: str = None) -> dict:
    """Fetch fresh fields for one item: name, sample count, additional-sample categories, date."""
    number_column_id = number_column_id or NUMBER_COLUMN_ID
    add_samples_column_id = add_samples_column_id or ADD_SAMPLES_COLUMN_ID
    date_column_id = date_column_id or DATE_COLUMN_ID
    query = """
    query ($itemId: [ID!], $columnIds: [String!]) {
      items(ids: $itemId) {
        id
        name
        column_values(ids: $columnIds) {
          id
          text
        }
      }
    }
    """
    column_ids = [c for c in (number_column_id, add_samples_column_id, date_column_id) if c]
    data = _run_query(query, {"itemId": [item_id], "columnIds": column_ids})
    items = data.get("items") or []
    if not items:
        raise ValueError(f"Item {item_id} not found")
    item = items[0]
    col_by_id = {c["id"]: c["text"] for c in item["column_values"]}

    n_samples_text = (col_by_id.get(number_column_id) or "0").strip()
    try:
        n_samples = max(0, int(float(n_samples_text)))
    except ValueError:
        n_samples = 0

    add_samples_text = col_by_id.get(add_samples_column_id) or ""
    add_samples = [s.strip() for s in add_samples_text.split(",") if s.strip()]

    date = col_by_id.get(date_column_id) or ""

    return {
        "id": item["id"],
        "name": item["name"],
        "n_samples": n_samples,
        "add_samples": add_samples,
        "date": date,
    }


if __name__ == "__main__":
    items = list_active_requests_items()
    print(f"Active Requests ({len(items)} items):\n")
    for item in items:
        fields = get_item_fields(item["id"])
        print(f"- {fields['name']}  |  N of samples: {fields['n_samples']}  |  Add. samples: {fields['add_samples']}")
