"""monday app backend: "When a subitem is created, connect it to its parent item".

Flow:
  1. User adds the recipe -> monday calls /trigger/subscribe. We register a create_subitem
     webhook on the board whose URL carries the trigger's webhookUrl (stateless: monday
     code has no secure storage for Python apps).
  2. Subitem created -> monday calls /webhook. We fire the trigger with the subitem id.
  3. monday runs the action -> /action/connect-parent. We look up the subitem's parent and
     set the subitems board's Connect column to it.
  4. Recipe deleted -> /trigger/unsubscribe removes the board webhook.

Run locally: MONDAY_SIGNING_SECRET=... MONDAY_APP_ID=... APP_BASE_URL=... python main.py
"""
import os
from urllib.parse import quote, urlparse

import requests
from flask import Flask, jsonify, request

import monday_api
from auth import trigger_auth_header, verify_request

# Public URL of this app, e.g. https://<id>.monday.app (shown by `mapps code:push`).
APP_BASE_URL = os.environ.get("APP_BASE_URL", "").rstrip("/")

app = Flask(__name__)


@app.get("/")
def health():
    return "ok"


@app.post("/trigger/subscribe")
def subscribe():
    claims = verify_request()
    payload = request.get_json()["payload"]
    board_id = payload["inputFields"]["boardId"]
    hook_url = f"{APP_BASE_URL}/webhook?trigger={quote(payload['webhookUrl'], safe='')}"
    try:  # one recipe per board: drop webhooks orphaned by earlier failed subscribes
        stale = monday_api.delete_app_subitem_webhooks(claims["shortLivedToken"], board_id)
        if stale:
            print(f"Board {board_id}: deleted stale webhooks {stale}", flush=True)
    except Exception as e:
        print(f"Stale webhook cleanup on board {board_id} failed: {e}", flush=True)
    webhook_id = monday_api.create_subitem_webhook(claims["shortLivedToken"], board_id, hook_url)
    print(f"Subscribed board {board_id}: webhook {webhook_id}", flush=True)
    return jsonify({"webhookId": webhook_id})


@app.post("/trigger/unsubscribe")
def unsubscribe():
    claims = verify_request()
    webhook_id = request.get_json()["payload"]["webhookId"]
    try:
        monday_api.delete_webhook(claims["shortLivedToken"], webhook_id)
    except Exception as e:  # webhook may already be gone; never block recipe deletion
        print(f"delete_webhook {webhook_id} failed: {e}", flush=True)
    print(f"Unsubscribed webhook {webhook_id}", flush=True)
    return "", 200


@app.post("/webhook")
def board_webhook():
    body = request.get_json()
    if "challenge" in body:  # monday verifies the URL when the webhook is created
        return jsonify({"challenge": body["challenge"]})

    event = body.get("event", {})
    trigger_url = request.args.get("trigger")
    host = urlparse(trigger_url or "").hostname or ""
    if not host.endswith(".monday.com"):  # only ever forward to monday
        print(f"Webhook without a valid trigger url: {trigger_url}", flush=True)
        return "", 200

    resp = requests.post(
        trigger_url,
        json={"trigger": {"outputFields": {"subitemId": int(event["pulseId"])}}},
        headers={"Authorization": trigger_auth_header()},
        timeout=15,
    )
    print(f"Subitem {event['pulseId']} created -> trigger {resp.status_code}", flush=True)
    return "", 200


@app.post("/action/connect-parent")
def connect_parent():
    claims = verify_request()
    token = claims["shortLivedToken"]
    subitem_id = str(request.get_json()["payload"]["inputFields"]["subitemId"])

    subitem = monday_api.get_subitem(token, subitem_id)
    if not subitem or not subitem.get("parent_item"):
        print(f"Item {subitem_id} not found or has no parent; skipping", flush=True)
        return "", 200

    parent = subitem["parent_item"]
    column = monday_api.find_parent_connect_column(subitem["board"]["columns"], parent["board"]["id"])
    if not column:
        print(f"No connect column to board {parent['board']['id']} on subitems board {subitem['board']['id']}", flush=True)
        return "", 200

    current = next((cv for cv in subitem["column_values"] if cv["id"] == column["id"]), {})
    linked = current.get("linked_item_ids") or []
    if parent["id"] in linked:
        return "", 200  # already linked

    # Keep anything already linked; just add the parent.
    monday_api.connect_items(token, subitem["board"]["id"], subitem_id, column["id"], [*linked, parent["id"]])
    print(f"Connected subitem {subitem_id} -> parent {parent['id']} ({column['title']})", flush=True)
    return "", 200


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 8080)))
