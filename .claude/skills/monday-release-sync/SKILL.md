---
name: monday-release-sync
description: Push a freshly-published GitHub Release (a built .exe/.zip for an internal XtraLit tool) onto the "Local Application Library" monday.com board so colleagues can find it. Use this skill whenever the user has just created/tagged a GitHub Release and wants it available on monday, or says things like "push this release to monday", "sync this to the app library", "update the board with the new build", "upload the release", or "put the new version on monday" — even if they don't use the word "skill." Trigger this proactively right after helping build/tag a release for an internal tool, by asking if they want it pushed to the board.
---

# Monday Release Sync

Takes the latest GitHub Release of an internal app and syncs it onto the
**Local Application Library** board in monday.com (workspace: **Lab Logistics**),
replacing the old build with the new one.

Two developers use this skill independently from their own machines — it has
no shared state, no CI secrets, and no per-repo config file. Auth is whatever
`gh` and the monday MCP connection are already using locally.

## Confirmed board reference (do not re-discover these — they're fixed)

- Workspace: **Lab Logistics** — id `4458956`
- Board: **Local Application Library** — id `5101737964`
- Columns on this board (same for every item, since columns are board-level):
  - `text_mm5zwec7` — **Version** (plain text)
  - `text_mm5zcfjm` — **Description** (plain text)
  - `file_mm5zfb9t` — **Files** (this is the release-zip column — confirmed via the
    existing `LabelPrinter` item, which already has its zip here)
  - `file_mm5zm44z` — a second, currently-empty File column of unknown purpose.
    **Do not touch this column** unless the user explicitly says what it's for.
  - `subtasks_mm5z70vc`, `pulse_log_mm63p7xg` — system columns, ignore.

If the board structure ever looks different from this (new/renamed columns,
column IDs that don't match), stop and tell the user rather than guessing.

## Workflow

### Step 1 — Detect the repo and release

Run from the app's repo directory (the directory the user is already in after
tagging/pushing a release):

```bash
git remote get-url origin
gh release view --json tagName,assets,name -R <owner>/<repo>
```

Parse `<owner>/<repo>` out of the remote URL (works for both
`https://github.com/owner/repo.git` and `git@github.com:owner/repo.git`).

Show the user one line before continuing, e.g.:
`Detected release: owner/repo @ v0.2.0 (asset: LabelPrinter-windows.zip)`

This is a lightweight echo, not a confirmation gate — don't stop and wait
unless something below fails.

**If `gh` isn't authenticated or the repo/release can't be found:** stop and
tell the user plainly (e.g. "no git remote found here — run this from inside
the app's repo folder", or "gh isn't authenticated, run `gh auth login`").
Don't guess a repo name.

**Picking the right asset:** `gh release view --json assets` only returns
assets that were actually uploaded to the release (GitHub's auto-generated
"Source code" zip/tarball are not part of this list, so you shouldn't need to
filter them out). If there's exactly one asset, use it. If there's more than
one, list them and ask the user which one is the distributable.

### Step 2 — Download the asset locally (temp only)

```bash
gh release download <tag> -R <owner>/<repo> -p '<asset-name>' -D /tmp/monday-release-sync
```

This is a scratch copy for the upload step — nothing needs to persist after
this skill finishes.

### Step 3 — List board items and let the user pick

Call `get_board_items_page` on board `5101737964` (no need for `includeColumns`
unless you want to show current versions alongside names). Present the item
names to the user and ask which one this release belongs to — don't guess
based on repo name matching, since the item name and repo name may differ.

**Nothing destructive happens before this point.** Do not clear or touch any
column until the user has explicitly picked (or created) an item.

### Step 4a — Existing item selected

1. Clear the Files column first:
   ```
   change_item_column_values(
     boardId=5101737964,
     itemId=<chosen id>,
     columnValues='{"file_mm5zfb9t": {"clear_all": true}}'
   )
   ```
   If this errors because the column is already empty, that's fine — proceed.
2. Update the Version column to the **exact git tag, including the "v" prefix**
   (e.g. `v0.2.0` — yes, this is inconsistent with the older `"1.1"` value on
   `LabelPrinter`; that's expected going forward, not a bug):
   ```
   change_item_column_values(
     boardId=5101737964,
     itemId=<chosen id>,
     columnValues='{"text_mm5zwec7": "v0.2.0"}'
   )
   ```
3. Leave the Description column untouched — only touch it for brand-new items
   (Step 4b).

### Step 4b — New app, no matching item yet

1. Ask the user what to name the item (don't assume it matches the repo name).
2. Write a short (one sentence) description yourself, generated from what you
   already know about the app from the current conversation/session context —
   don't ask the user to write it.
3. Create the item with Version + Description set in the same call:
   ```
   create_item(
     boardId=5101737964,
     name="<user-provided name>",
     columnValues='{"text_mm5zwec7": "v0.2.0", "text_mm5zcfjm": "<short auto description>"}'
   )
   ```
4. Use the returned item id for the upload in Step 5. No clear-step needed —
   it's a brand-new item with an empty Files column.

### Step 5 — Upload the new file

```
get_asset_upload_url(
  contentType="application/zip",
  fileName="<asset filename, e.g. LabelPrinter-windows.zip>",
  fileSize=<bytes>
)
```
Then PUT the local file to the returned `upload_url`:
```bash
curl -i -X PUT "<upload_url>" -H "Content-Type: application/zip" --data-binary @/tmp/monday-release-sync/<asset-name>
```
Capture the `ETag` response header, then:
```
finalize_asset_upload(
  boardId=5101737964,
  itemId=<id>,
  columnId="file_mm5zfb9t",
  uploadId=<from get_asset_upload_url>,
  etag=<from the PUT response>
)
```

### Step 6 — Confirm

Tell the user the item name, new version, and give the item's monday URL
(`https://xtralit-team.monday.com/boards/5101737964/pulses/<item id>`).

## Edge cases

- **File over 500MB:** monday's API hard-limits uploads to 500MB
  (`get_asset_upload_url`'s `fileSize` param enforces this too). Stop and tell
  the user — this shouldn't happen for these apps (current build is ~18.5MB)
  but don't silently truncate or retry.
- **No releases found for the repo:** tell the user directly; don't fall back
  to an older release or a different repo.
- **Multiple real assets, ambiguous which is the distributable:** ask, don't
  guess by file extension alone (a repo could reasonably ship two zips).
- **Clean-up:** delete `/tmp/monday-release-sync` contents after a successful
  run so repeated invocations don't accumulate old zips.
