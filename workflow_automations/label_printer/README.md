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
   item.

## Config (`.env`)

| Var | Meaning |
|---|---|
| `MONDAY_API_TOKEN` | Personal API token (Admin → API) |
| `BOARD_ID` | Target board id |
| `GROUP_ID` | Internal id of the "Active Requests" group (not the display title) |
| `NAME_COLUMN_ID`, `NUMBER_COLUMN_ID` | Column ids holding the printable fields |
| `PRINTER_IP` | LAN IP of the QL-820NWBc |
| `PRINTER_MODEL` | `QL-820NWB` |
| `LABEL_SIZE` | `brother_ql` label code matching the loaded stock (endless/die-cut) |

## Out of scope for this POC

Multi-machine distribution, auto-start/background service, web page auth,
other boards/groups.
