---
name: monday-board-documentation
description: Generates short, non-technical documentation for one monday.com board, or a group of similarly-structured boards, and posts it as a real monday Doc filed in a "Documentation" folder in the relevant workspace. Use this skill whenever the user asks to "document a board," "create board documentation," "explain this board," or names a specific monday.com workspace/board(s) they want documented. Requires the monday.com MCP connection to be active.
---

# Monday.com Board Documentation Generator

## Purpose
Produce a short, colleague-friendly explanation of what a monday.com board (or a group of similar boards) is, how it works, and what to watch out for — then post it as a standalone monday Doc, never by modifying the board(s) themselves.

## Hard safety constraint — read this before calling any tool

This skill may **only add new content** (a folder, a doc, blocks inside the doc it just created). It must **never edit or erase anything on an existing board or item**. Concretely:

- Allowed: read-only tools (get_board_info, get_board_items_page, list_automations, etc.), `create_folder`, `create_doc`, and `update_doc` calls that target the doc this skill just created (e.g. fixing a typo in the same session).
- Never call: `update_items`, `change_item_column_values`, `create_column`, `create_item`/`create_items`, `move_object`, `delete_action`, `run_action`, `manage_automations`, `update_view`/`create_view`, `update_board`, or any `delete_blocks`/`replace_block` against a doc this skill did not itself create in this session.
- If a step seems to require modifying the board (e.g. "attach this to the board as a tab"), do not do it — that's exactly the kind of API dead-end this skill exists to avoid. Post as a standalone Doc instead and link to it.

### Step 1: Confirm target and mode
Ask the user:
1. Which **workspace** and **board(s)** to document.
2. Whether this is a **single board** or a **group of similar boards** (same structure, documented together in one doc).

Use the monday MCP tools to look up the matching board(s). **Before doing anything else, show the user what you found (board name(s), workspace, board ID(s)) and ask them to confirm it's right.** Do not proceed until confirmed — board/workspace names can collide, and for a group, confirm the full list of boards going into the doc.

### Step 2: Gather context
For each board, pull:
- Full board structure (all columns, their types, and labels/options)
- Board-level permission settings (who can view/edit)
- The board's views (list all, note type of each — Table, Kanban, Doc, Chart, etc.)
- Active automations on the board (trigger → action, in plain terms)
- 5 sample items, **including their subitems**, to understand real usage patterns (not just schema)

If any of the above is not accessible via the current MCP permissions, note that gap to the user rather than guessing.

For a **group of boards**, also work out what's shared structure vs. what differs per board — you'll need this split for Step 3.

### Step 3: Write the documentation
Audience: **non-technical colleagues.** Assume they use the board(s) daily but have never thought about the underlying setup.

**Tone rules:**
- Short, plain language. No jargon (no "schema," "automation trigger conditions," etc. — describe in everyday terms).
- Emoji are allowed only as a small visual emphasis *next to* important text (e.g., a warning, a key status) — never replacing the actual words, and never decorative filler. Use sparingly and only where it adds clarity.
- Target length: **300–500 words total per board, hard cap 500 per board** — excluding the "How the formulas work" section, which is sized separately (see below).

**Document opening:** Always start the doc by listing the board(s) it covers by name (and a link if available) — for a single board that's one line; for a group, list all of them up front so the reader immediately knows the doc's scope.

**Where the weight goes:** on these boards, the item-level columns are usually just project-management scaffolding — status, owner, timeline, the experiment's setup/spec values. The *real* content — the measurements and the calculations run on them — usually lives on subitems (or wherever the formula/number-heavy columns actually are). Don't give both equal space by default. Identify which level (item or subitem) actually carries the raw results and formulas, and give that level the bulk of the explanation; keep the project-management-flavored columns brief. If a board doesn't split this way (no subitems, or the item level *is* the data), skip this distinction and just document the columns as they are.

**Single board** — required sections (skip a section only if genuinely not applicable):

1. **What this board is for** — 1-2 sentence plain-language purpose, inferred from structure + sample items.
2. **Setup & tracking columns** — the project-management layer: status, owner, timeline, and the setup/spec values that describe *what was run* (not the results). Keep this tight — a line or short list per column, not deep explanation. Skip minor/decorative columns entirely.
3. **Measurements & results** — the columns that actually hold the raw data and calculated outputs (often on subitems). This is the board's core content — give it the most space and detail: what gets measured, what units, and what each derived/rollup number means in practice.
4. **How the formulas work** — only include this section if the board has formula columns. Many boards repeat the same formula pattern once per variable (e.g. one per ion/element) — don't explain each repetition separately. Group by *pattern*: identify each distinct formula logic, give **one worked example** (using one variable's actual formula) and explain what it computes and why, then just list which other columns reuse that same pattern. This section isn't bound by the word cap below — size it to however many distinct patterns actually exist, but stay just as plain-language as the rest (explain the logic in words, not just paste the formula).
5. **Views on this board** — list the views and what each is useful for ("Kanban view — see items grouped by status", etc.).
6. **Permissions** — who can see/edit this board, in plain terms.
7. **Automations** — call `list_automations` (covers both live workflows and legacy/read-only ones — present both together, never label either "legacy"). Describe each as "when X happens, Y happens," in plain language, not raw config. Never omit this section — if the board has zero automations, say so explicitly ("No automations configured on this board").
8. **Watch out for** — potential breaking points or mistakes: fragile automations (e.g., one relies on an exact label match), confusing status logic, columns that look similar and could be mixed up (e.g. an item-level rollup vs. the subitem-level raw column it's rolled up from), permission gaps, or anything structurally unusual on this board. This is a general risk-flagging section, not limited to automations.
9. **Anything unique** — any board-specific quirk not covered above worth flagging.

**Group of similar boards** — since a group is only chosen when the boards share the same structure, write the shared explanation once, then call out per-board differences:

1. Sections 1-8 above, written **once**, covering the shared structure/purpose/columns/formulas/views/permissions/automations that apply across all the boards in the group.
2. A **Differences between boards** section: for each board, what's different in practice (e.g. different owners, slightly different automations, different label sets, different volume/usage pattern). Keep each board's entry tight — a few bullets, not a full re-explanation.
3. **Watch out for** and **Anything unique**, written once, folding in anything from any individual board worth flagging.

### Step 4: Get approval before writing anything
**Always show the full draft (including the board list at the top) in chat and wait for the user's explicit go-ahead before creating any folder or doc.** This applies every time, single board or group — no exceptions. If the user asks for changes, revise and re-show before proceeding.

### Step 5: Post the documentation
Once approved:

1. Call `workspace_info` on the target workspace to check whether a folder named **"Documentation"** already exists.
2. If it doesn't exist, create it with `create_folder` (name exactly "Documentation") in that workspace.
3. Call `create_doc` with `location: "workspace"`, the target `workspace_id`, `folder_id` set to the Documentation folder, `doc_kind: "public"`, and the approved markdown. Name the doc after the board (single) or a descriptive group name (group) — do not reuse "Board Documentation" as a literal doc name across multiple docs in the same folder, since that makes them indistinguishable in the folder listing.
4. If a board spans a workspace different from others in a group (shouldn't normally happen, but check), file the doc in the workspace of the primary/first-listed board and say so to the user.
5. Give the user the doc's URL from the `create_doc` response.

Do not fall back to adding a Dashboard-type view/tab on the board, and do not create an item + update for this — `create_doc` is the only posting path this skill uses.

## Notes
- Never skip the Step 1 confirmation, even if the user sounds certain — board name collisions across workspaces are the main failure mode here.
- If sample items reveal a board is used very differently from what the column schema suggests, trust the actual usage pattern over the schema when writing "What this board is for."
- A "group" should only be used when the boards genuinely share structure. If the user asks to group boards that turn out to have materially different columns/purpose, flag that before writing and suggest separate docs instead.
