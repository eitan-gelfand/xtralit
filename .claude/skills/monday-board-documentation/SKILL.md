---
name: monday-board-documentation
description: Generates short, non-technical documentation for a monday.com board and posts it as a new Dashboard-type board view (named "Board Documentation") on that board. Use this skill whenever the user asks to "document a board," "create board documentation," "explain this board," or names a specific monday.com workspace/board they want documented. Requires the monday.com MCP connection to be active.
---

# Monday.com Board Documentation Generator

## Purpose
Produce a short, colleague-friendly explanation of what a monday.com board is, how it works, and what to watch out for — then post it directly into the board as a new Doc view.

## Workflow

### Step 1: Confirm target
Ask the user for the **workspace name** and **board name** if not already given.
Use the monday MCP tools to look up the matching board.
**Before doing anything else, show the user the board you found (name, workspace, board ID) and ask them to confirm it's the right one.** Do not proceed until confirmed — board/workspace names can collide.

### Step 2: Gather context
Once confirmed, pull:
- Full board structure (all columns, their types, and labels/options)
- Board-level permission settings (who can view/edit)
- The board's views (list all, note type of each — Table, Kanban, Doc, Chart, etc.)
- Active automations on the board (trigger → action, in plain terms)
- 5 sample items, **including their subitems**, to understand real usage patterns (not just schema)

If any of the above is not accessible via the current MCP permissions, note that gap to the user rather than guessing.

### Step 3: Write the documentation
Audience: **non-technical colleagues.** Assume they use the board daily but have never thought about its underlying setup.

**Tone rules:**
- Short, plain language. No jargon (no "schema," "automation trigger conditions," etc. — describe in everyday terms).
- Emoji are allowed only as a small visual emphasis *next to* important text (e.g., a warning, a key status) — never replacing the actual words, and never decorative filler. Use sparingly and only where it adds clarity.
- Target length: **300–500 words total, hard cap 500.**

**Required sections (skip a section only if genuinely not applicable):**

1. **What this board is for** — 1-2 sentence plain-language purpose, inferred from structure + sample items.
2. **Key columns** — only the columns that actually drive the workflow (status columns, key dates, owner/person columns). Skip minor/decorative columns. Explain what each one means in practice.
3. **Views on this board** — list the views and what each is useful for ("Kanban view — see items grouped by status", etc.).
4. **Permissions** — who can see/edit this board, in plain terms.
5. **Automations** — call `list_automations` (covers both live workflows and legacy/read-only ones — present both together, never label either "legacy"). Describe each as "when X happens, Y happens," in plain language, not raw config. Never omit this section — if the board has zero automations, say so explicitly ("No automations configured on this board").
6. **Watch out for** — potential breaking points or mistakes: fragile automations (e.g., one relies on an exact label match), confusing status logic, columns that look similar and could be mixed up, permission gaps, or anything structurally unusual on this board. This is a general risk-flagging section, not limited to automations.
7. **Anything unique** — any board-specific quirk not covered above worth flagging.

### Step 4: Post the documentation
monday's public API cannot create a native Doc-type board view (`create_view`'s `ViewKind` only supports `DASHBOARD`, `TABLE`, `FORM`, `APP` — Doc tabs are UI-only) and cannot create a plain text/notes widget either (the real `ExternalWidget` enum only has `CHART`, `NUMBER`, `BATTERY`, `CALENDAR`, `GANTT`, `LISTVIEW`, `APP_FEATURE`). So instead:

1. Call `create_view` with `type: "DASHBOARD"` on the target board, named exactly **"Board Documentation"**. This adds a dashboard-type tab directly on the board.
2. Give the user the finished write-up as plain copy-ready text in the chat response.
3. Tell them to open that new tab, add a Text widget (2 clicks), and paste the text in — that's the accepted final step, not a fallback to apologize for.

Do not create an item + update for this instead unless the user explicitly asks for that specific route.

## Notes
- Never skip the Step 1 confirmation, even if the user sounds certain — board name collisions across workspaces are the main failure mode here.
- If sample items reveal the board is used very differently from what the column schema suggests, trust the actual usage pattern over the schema when writing "What this board is for."
