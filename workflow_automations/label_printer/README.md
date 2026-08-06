# Label Printer POC

Pulls analytical probing request names/numbers from a monday.com board and
prints them directly to a Brother QL-820NWBc network label printer, replacing
manual retyping into Brother P-touch.

## Setup

```bash
cd workflow_automations/label_printer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in values, see below
```

## Build order

1. `printer/` — standalone script, prints one hardcoded test label. Verify
   physically before moving on.
2. `monday/` — standalone script, lists Active Requests items and fetches a
   single item's fields. Verify terminal output matches the board.
3. `label/` — combines 1 + 2: renders real monday data onto a label image
   sized/laid out for the loaded stock, sends to printer.
4. `app/` — Flask app tying it all together with a "Print Label" button per
   item. Runs on `http://127.0.0.1:5050` (not 5000 - macOS AirPlay Receiver
   uses that port).

## Config (`.env`)

| Var | Meaning |
|---|---|
| `MONDAY_API_TOKEN` | Personal API token (Admin → API) |
| `BOARD_ID` | Target board id |
| `GROUP_ID` | Internal id of the "Active Requests" group (not the display title) |
| `NAME_COLUMN_ID` | Unused - item name comes from monday's built-in `name` field |
| `NUMBER_COLUMN_ID` | Column id for "N of samples" |
| `ADD_SAMPLES_COLUMN_ID` | Column id for the "Add. samples" dropdown |
| `DATE_COLUMN_ID` | Column id for the request date (defaults to `date4` if unset) |
| `PRINTER_IP` | LAN IP of the QL-820NWBc (set it static on the printer/router - it changed twice during POC dev and broke printing until re-discovered) |
| `PRINTER_MODEL` | `QL-820NWB` |
| `LABEL_SIZE` | `brother_ql` label code matching the loaded stock (endless/die-cut) |

Any column id left unset is simply excluded from the monday query rather than
sent as null (which the API would reject).

## Label content and print logic

For one monday item, `label/render.py` builds one physical label per:
- sample, numbered 1..N ("N of samples")
- selected "Add. samples" category (e.g. EL, Brine)

Each label is `<item name> - <number or category>` on a wrapped row, plus a
`date: <request date>` row below. Image height is computed from the actual
content per label, so short labels don't carry blank space on the roll.

The name wraps at word boundaries first, then at hyphens (this board's item
names are usually one hyphenated token with no spaces, e.g.
`1R-DS-TOE40(106-250)-70(2)-Li`), then falls back to a character-level split
as a last resort for a single run with neither - this is what keeps long
names from being clipped off the edge of the label instead of wrapping.

## Known printer quirks

- Consecutive print jobs are paced 3s apart (`printer.send.print_images`) -
  sending them back-to-back gets the next connection refused before the
  printer has finished cutting the previous label.
- The network backend has no read-back channel, so a successful `print_image`
  call always reports `did_print: False` / `ready_for_next_job: False` - that
  is expected, not a failure. An exception (connection refused/timed out) is
  the only real failure signal this backend gives.
- All sockets the process opens have a 10s timeout, so an unreachable printer
  fails fast instead of hanging the Flask request thread.

## Running the web app

```bash
python app/main.py   # http://127.0.0.1:5050
```

Debug/auto-reload is off by default - Werkzeug's reloader forks a child
process, and if it's killed incompletely (e.g. Ctrl+C mid-print) it can leave
a stale process holding the port that silently keeps serving old code. Set
`LABEL_PRINTER_DEBUG=1` for auto-reload while iterating on templates/routes,
and prefer `pkill -f "app/main.py"` over Ctrl+C if a restart seems to not be
picking up changes.

## Distributing to non-technical Windows colleagues

Board/printer config (board/group/column ids, printer model, label size) is
baked into `monday/client.py` / `printer/send.py` as defaults, since it's
shared and not secret. Only two things are meant to live in a per-user
`settings.env` sitting next to the executable:

- `MONDAY_API_TOKEN` - secret, personal, tied to that person's monday.com
  account and board permissions. Never bake one person's token into a
  binary shared with others: it's not board-scoped (a leak/decompile
  exposes their whole monday account), it breaks for everyone if revoked,
  and it misattributes everyone's activity to one person. Since colleagues
  already have their own monday.com logins with access to this board, each
  person should generate their own personal token instead (Admin → API).
- `PRINTER_IP` - not secret, but has already changed twice during this
  project (sleep/wake, then a static-IP change), so it stays editable
  rather than baked in.

`settings.env` is never bundled inside the exe and is gitignored - it's
created per-machine from `settings.env.example` + `SETUP.txt` (the
non-technical setup guide shipped alongside the exe).

The exe is built via `.github/workflows/build-windows.yml` on GitHub
Actions' `windows-latest` runner (PyInstaller can't cross-compile, so this
runs on push instead of locally on the Mac dev machine). That CI runner has
no access to the lab LAN, so it only proves the exe builds and launches -
not that it reaches monday.com or the printer. A real end-to-end smoke test
on an actual Windows machine on the lab network is still required after
each build.

`app/main.py`'s entrypoint is frozen-aware (`sys.frozen`/`sys._MEIPASS`) so
the same file serves both `python app/main.py` (dev) and the packaged
`LabelPrinter.exe` - it resolves `settings.env` and the Flask template
folder relative to the exe's location rather than assuming a dev checkout,
and opens the default browser automatically on start.

## Out of scope for this POC

Auto-start/background service, web page auth, other boards/groups, code
signing (unsigned exe triggers a Windows SmartScreen warning - documented
as an expected step in SETUP.txt, not fixed here).
