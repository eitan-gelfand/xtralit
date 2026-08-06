"""Step 4: single-page Flask app - list Active Requests items, print on click.

Run: python app/main.py, then open http://127.0.0.1:5050
(not port 5000 - macOS AirPlay Receiver listens there)
"""
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify

from monday.client import list_active_requests_items, get_item_fields
from label.render import build_labels_for_item
from printer.send import print_images

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


@app.route("/")
def index():
    try:
        items = list_active_requests_items()
        error = None
    except Exception:
        app.logger.exception("Failed to load Active Requests from monday.com")
        items = []
        error = "Couldn't load items from monday.com - check the connection/token and reload."
    return render_template("index.html", items=items, error=error)


@app.route("/print/<int:item_id>", methods=["POST"])
def print_item_route(item_id):
    try:
        fields = get_item_fields(str(item_id))  # re-fetch fresh, don't trust list-load data
        labels = build_labels_for_item(fields)
        if not labels:
            return jsonify(ok=False, message=f"{fields['name']}: nothing to print (0 samples, 0 add. samples)")

        print_images(labels)

        return jsonify(ok=True, message=f"{fields['name']}: printed {len(labels)} label(s)")
    except Exception as exc:
        app.logger.exception("Print failed for item %s", item_id)
        return jsonify(ok=False, message=f"Print failed: {exc}"), 500


if __name__ == "__main__":
    # debug/reloader off by default: the reloader forks a child process that,
    # if killed incompletely (e.g. Ctrl+C during a print), leaves a stale
    # process holding port 5050 that silently serves old code on next start.
    # Set LABEL_PRINTER_DEBUG=1 for dev-time auto-reload when iterating on
    # templates/routes.
    debug = os.environ.get("LABEL_PRINTER_DEBUG") == "1"
    app.run(host="127.0.0.1", port=5050, debug=debug, threaded=True)
