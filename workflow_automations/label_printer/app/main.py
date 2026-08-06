"""Step 4: single-page Flask app - list Active Requests items, print on click.

Run: python app/main.py, then open http://localhost:5000
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify

from monday.client import list_active_requests_items, get_item_fields
from label.render import build_labels_for_item
from printer.send import print_images

app = Flask(__name__)


@app.route("/")
def index():
    items = list_active_requests_items()
    return render_template("index.html", items=items)


@app.route("/print/<item_id>", methods=["POST"])
def print_item_route(item_id):
    try:
        fields = get_item_fields(item_id)  # re-fetch fresh, don't trust list-load data
        labels = build_labels_for_item(fields)
        if not labels:
            return jsonify(ok=False, message=f"{fields['name']}: nothing to print (0 samples, 0 add. samples)")

        print_images(labels)

        return jsonify(ok=True, message=f"{fields['name']}: printed {len(labels)} label(s)")
    except Exception as exc:
        return jsonify(ok=False, message=f"Print failed: {exc}"), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
