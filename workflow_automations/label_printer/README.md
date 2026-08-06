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

## Out of scope for this POC

Multi-machine distribution, auto-start/background service, web page auth,
other boards/groups.
