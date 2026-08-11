"""Step 4: single-page Flask app - list Active Requests items, print on click.

Dev: python app/main.py, then open http://127.0.0.1:5050
(not port 5000 - macOS AirPlay Receiver listens there)

Packaged (PyInstaller): double-click LabelPrinter.exe - the browser opens
automatically. Board/printer defaults are baked in; only MONDAY_API_TOKEN
needs to be supplied per-user via settings.env next to the executable.
"""
import logging
import os
import sys
import threading
import traceback
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if getattr(sys, "frozen", False):
    # Set up before anything else so even an import-time crash below gets
    # logged: the frozen build has no console window (see build workflow's
    # --noconsole), so this file is the only way to see what happened.
    # Truncated (not appended) on every start - see Step 2 commit for why.
    try:
        _log_path = os.path.join(os.path.expanduser("~"), "label_printer_log.txt")
        logging.basicConfig(filename=_log_path, filemode="w", level=logging.INFO)
        sys.stdout = open(_log_path, "a")
        sys.stderr = sys.stdout
    except Exception:
        pass  # best-effort - a broken home dir shouldn't block startup
else:
    logging.basicConfig(level=logging.INFO)


def _pause_on_crash(exc: BaseException):
    """No console window in the frozen build (--noconsole) to print a
    traceback into or read a keypress from - the app would just vanish with
    no explanation. Log the exception (logging is set up above, before this
    can be reached) and show a native message box instead. In dev, the
    traceback stays on the real console and exiting immediately is fine."""
    if getattr(sys, "frozen", False):
        logging.error("Fatal error", exc_info=(type(exc), exc, exc.__traceback__))
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Label Printer crashed:\n\n{exc}\n\n"
                f"See label_printer_log.txt in your home folder for details.",
                "Label Printer - Error",
                0x10,  # MB_ICONERROR
            )
        except Exception:
            pass
    else:
        traceback.print_exception(type(exc), exc, exc.__traceback__)
    sys.exit(1)


def _settings_env_path() -> str:
    """settings.env lives next to the running executable (frozen build) or
    next to the label_printer/ project root (dev). Never bundled inside the
    exe itself - it's per-user/per-machine and holds the personal API token."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "settings.env")


try:
    from dotenv import load_dotenv

    # Must run before importing monday.client / printer.send, whose own
    # load_dotenv() calls at import time won't override already-set env vars.
    load_dotenv(_settings_env_path())

    from flask import Flask, render_template, jsonify

    from monday.client import list_active_requests_items, get_item_fields
    from label.render import build_labels_for_item
    from printer.send import print_images

    # PyInstaller extracts bundled data files (see --add-data in the build
    # workflow) into a temp dir exposed as sys._MEIPASS; Flask's automatic
    # template-folder detection isn't reliable there, so point it explicitly.
    if getattr(sys, "frozen", False):
        _template_folder = os.path.join(sys._MEIPASS, "templates")
    else:
        _template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

    app = Flask(__name__, template_folder=_template_folder)
except Exception as exc:
    _pause_on_crash(exc)

APP_URL = "http://127.0.0.1:5050"


@app.route("/")
def index():
    if not os.environ.get("MONDAY_API_TOKEN"):
        return render_template(
            "index.html", items=[],
            error=f"No monday.com API token configured. Add it to settings.env "
                  f"({_settings_env_path()}), then restart the app.",
        )
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
    try:
        # debug/reloader off by default: the reloader forks a child process
        # that, if killed incompletely (e.g. Ctrl+C during a print), leaves a
        # stale process holding port 5050 that silently serves old code on
        # next start. Set LABEL_PRINTER_DEBUG=1 for dev-time auto-reload
        # while iterating on templates/routes.
        debug = os.environ.get("LABEL_PRINTER_DEBUG") == "1"

        # With the reloader on, this module runs twice (monitor + worker);
        # only open the browser in the actual worker process to avoid two tabs.
        if not debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            threading.Timer(1.5, lambda: webbrowser.open(APP_URL)).start()

        print("Label Printer is running.")
        print(f"If your browser doesn't open automatically, go to {APP_URL}")
        print("Keep this window open while printing. Close it to stop.")

        if debug:
            # Waitress has no reloader; keep Flask's dev server for LABEL_PRINTER_DEBUG=1.
            app.run(host="127.0.0.1", port=5050, debug=True, threaded=True)
        else:
            from waitress import serve
            serve(app, host="127.0.0.1", port=5050, threads=4)
    except Exception as exc:
        _pause_on_crash(exc)
