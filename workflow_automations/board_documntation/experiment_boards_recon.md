# Experiment Board Reconnaissance — Static Boards (Pass 1)

Source: live monday.com API via `get_board_info` on the three Static boards, 2026-08-09.

## Board identity

| Board | ID | Items | Groups | Subitems board ID |
|---|---|---|---|---|
| Static Granulated Lots💣 | 1727424192 | 8 | General View, New Lots | 1727424202 |
| Static Ashkelon Lots🏭 | 1718296454 | 44 | General View, New Lots | 1718296482 |
| Static Mineral Lots | 1673451104 | 5 | New Lots, In Work (order flipped — In Work is not top group here) | 1673451224 |

## Item-level columns (constants) — side by side

All three share this backbone, in the same functional order: Name → Subitems → Status → Timeline → Experiment Duration (numbers, "days") → Sorbent Percentage (numbers, %) → Temperature (numbers) → Time Regime (numbers, "Hr") → Acid Type (dropdown) → Person → a block of `avg *` mirror columns → `link to Experiment Requests/Request Portal` (board_relation → 1943662705) → Item ID.

Drift found:
- **Granulated** and **Mineral** each also carry a `link to Li -> H Form` board_relation (→ board 1686249479). **Ashkelon does not have this column at all.**
- **Ashkelon** has an extra `Item to move` checkbox column not present on the other two.
- **Mineral** has an extra plain `Checkbox` column not present on the other two, and its Acid Type dropdown is `limit_select: true` (single-select) while Granulated/Ashkelon's Acid Type dropdowns allow multi-select (no limit set).
- Acid Type dropdown **label sets differ per board** (expected — different sorbent/acid combos per lot type), but the label *strings* are inconsistently formatted where they do overlap: Mineral has both `"H2S04 0.5M"` and `"HNO3 0.5M"` (zero for O in H2S04) while Granulated has `"H2S04 0.5M"` and also `"H2SO4 0.5M"` (letter O) as two *separate* labels — i.e. Granulated's own dropdown has a typo'd duplicate label sitting next to the correct one. Real drift, worth flagging to the user, not just cross-board.
- Groups are named identically ("General View", "New Lots") on Granulated/Ashkelon, but Mineral additionally has "In Work" instead of "General View" (same purpose, different label) and its group order is reversed (New Lots is top group, not General View).
- Temperature unit label differs cosmetically: Granulated/Mineral use `"  °"` (double space + degree, no C), Ashkelon uses `" °C"`.
- Mirror block order/count is functionally identical across all three (avg E,Li / avg Sorbent Losses % / avg Mn in eluate / avg E,Mg / avg E,Ca / avg E,Na / avg E,K / avg Li/Ca / avg Li/Mn / avg Li/Na / avg Li/Mg / avg Li/K / Cycle Count) — column **titles** vary in cosmetic ways only ("avg Li/Ca" vs "Li/Ca" — Granulated/Mineral prefix "avg", Ashkelon's own naming is inconsistent between "avg Li/Ca" and bare "Li/Na"/"Li/Mg" for two of its own mirror columns). This is naming inconsistency, not structural drift — the underlying `displayed_column` + `function: average` target is identical everywhere.

## Subitem-level columns — side by side

All three share this backbone: Name → Date → Done by (people) → Cycle (numbers) → sorbent percentage (numbers, %) → Brine Li (numbers) → pH (numbers) → Sorbent Mass (numbers, "g") → empty probe (numbers, "g") → full probe (numbers, "g") → Raw Vol (formula) → Na/K/Ca/Mg/Li/Mn (ppm, numbers) → 12 formula columns (E,Li / E,Mn / Mn in eluate / Sorbent Losses % / E,Na / E,K / E,Ca / E,Mg / 5x M-ratio / 5x mass-ratio).

**pH is a subitem-level plain `numbers` column on all three boards, with no item-level pH column anywhere.** This answers open question 5 for this category: within Static boards, pH is consistently treated as dynamic/per-cycle — no variation between these three.

### Formula string comparison (the important part)

Confirmed **not identical** in several places — same intent, different math:

1. **`E, *` formulas (E,Li / E,Mn / E,Na / E,K / E,Ca / E,Mg)** — mg/g normalized by active sorbent:
   - Granulated: `{X} * {raw_vol} / 1000 / ({sorbent_mass} * {sorbent_pct})` — divides by sorbent mass × sorbent %.
   - Ashkelon: `{X} * {raw_vol} / 1000 / {sorbent_mass}` — **does not divide by sorbent percentage at all.**
   - Mineral: same as Ashkelon (`/ {sorbent_mass}` only, no `* {sorbent_pct}`).
   - So Granulated's E,* formulas are normalized for active-sorbent content; Ashkelon and Mineral's are not. **Confirmed with the board owner: deliberate, not drift** — different sorbent types legitimately need different normalization. The audit skill should NOT flag sorbent-% term presence/absence in E,* formulas as an error across Static-category boards; treat both forms as valid, board-specific conventions.

2. **"Sorbent Losses %" formula** — Granulated and Ashkelon divide by `(10000 * {sorbent_mass} * 54.93)` — i.e. still no sorbent-% term in the denominator here (consistent within each board's own convention: Granulated actually does NOT include sorbent_pct in this one formula, breaking its own internal pattern from #1). Mineral is identical to these two. So all three actually agree on Sorbent Losses % (no sorbent_pct term) — it's specifically the **E,\* formulas** where Granulated diverges from the other two.

3. **"Mn in eluate" formula** — three different denominators:
   - Granulated: `/ 10000 / ({sorbent_mass} * {sorbent_pct})`
   - Ashkelon: `/ {sorbent_pct} / (10000 * {sorbent_mass})` — algebraically the same as Granulated's, just reordered. Equivalent.
   - Mineral: `/ 10000 / {sorbent_mass}` — **missing the `/ {sorbent_pct}` term entirely.** Real numeric drift, not just reordering.

4. **M-ratio formulas (Li/Ca, Li/Mn, Li/K, Li/Mg, Li/Na)** — Granulated and Ashkelon use bare `IF({li}>0, ..., "")`. **Mineral wraps every M-ratio formula in `IF(AND({li}>0, {X}>=0.1), ..., "N/A")`** — an added minimum-concentration guard and a different empty-value sentinel (`"N/A"` string vs empty string `""`). This changes both the trigger condition and the output type for edge cases (e.g. `{ca}=0.05, {li}=5` → Granulated/Ashkelon compute a huge ratio, Mineral returns `"N/A"`).

5. **Mass-ratio formulas (Li/Mn, Li/Ca, Li/K, Li/Mg, Li/Na as plain mass ratios)** — identical across all three, verbatim.

6. **Raw Vol formula** — identical across all three: `{full_probe} - {empty_probe}`.

### Mirror function types
All mirror columns use `function: "average"` except `Cycle Count`, which uses `function: "count"` on all three — consistent.

## Connect/mirror board targets found

- All three connect item-level `link to Experiment Requests/Request Portal` → board **1943662705**.
- Granulated and Mineral also connect `link to Li -> H Form` → board **1686249479**. Ashkelon does not have this column.
- **None of the three connect to Brines DataBase (1142444759).** Brine Li is typed by hand as a plain subitem `numbers` column on all three — answers open question 4: no automatic connection to the brine ground-truth board exists yet in this category.

## Answering the doc's open questions — Static-board part

- **Q4 (Brines DataBase connection):** No. Confirmed above — brine values are hand-typed, not connected.
- **Q5 (pH item vs subitem):** Within Static boards specifically, always subitem-level, all three, no exceptions.

---

# Pass 2 — Automatic Protocol, Column category, Sorption category, 3-Sample Machine

## Answering the remaining open questions

**Q1 (Pulsation Column Test Board listed twice):** Resolved via `workspace_info` on the Laboratory workspace (260935) — it exists exactly once, id 1675579239, in the Tests folder. The double listing in the original board inventory was a typo, not two boards. Note this board is structurally unlike every other board in this project: item terminology is "Cycle" (not "item"), there is no Status/Timeline/Duration/Acid-Type backbone at all — just Sorption Base (status), Desorption Acid (dropdown), Sorption/Desorption Vol/Speed. Its subitems track Sorption vs Desorption phases with Time/Vol/PH/Li — no formula columns at all, no mirrors. This looks like an early prototype board, structurally closer to a scratch test than the standardized experiment-board pattern. Flag as out-of-family in the audit rather than trying to fit it to the standard.

**Q2 (Sorption Column emphasis):** This board is the one Column-category board that **directly connects to Brines DataBase** via `board_relation` + 5 mirror columns (Brine Li/Na/K/Ca/Mg), rather than hand-typing brine values — unlike every Static/Automatic-Protocol/other-Column board, which either hand-type brine values or don't reference brine at all. Its subitem formulas center on **Bed Volumes (BV)**: `BV = ROUND(Total Volume / Sorbent Vol, 1)` — a metric no other board in the inventory computes. Combined with per-sample pH and "Adsorbed Li" (`Brine Li − Sample Li`), this board is emphasizing **breakthrough-curve tracking as brine passes through a fixed sorbent bed**, measured in bed-volumes-processed rather than fixed cycle count — the column-specific analog of what cycles are to the Static boards.

**Q3 (Cycle Data - 3 Sample Experiments "extreme case"):** Structurally this is a **three-tier hierarchy**, one level deeper than every other board in the inventory:
1. **Meta Board - 3 Sample Experiments** (item level) = the experiment constants, same role as a Static board's item level.
2. **Cycle Data - 3 Samle Experiments** = each *cycle* is a full cross-board-linked **item** (via `board_relation` back to Meta Board), not a subitem — this is the deviation. Every other board in the inventory keeps "cycle" at the subitem level.
3. Cycle Data's own **subitems** = each individual **sample** within that cycle (subitem column literally titled "Sample", numeric).

So where Static/Column boards go item (experiment) → subitem (cycle), this family goes item (experiment) → item (cycle, separate board) → subitem (sample within cycle). That's the "extreme case" — cycle granularity got promoted a full tier, because this experiment protocol takes multiple samples *within* a single cycle, which the standard two-tier item/subitem model can't represent. Currently thin on data (Meta Board has 1 item, Cycle Data has 27 items/cycles) — likely still being built out.

## Column-category family (Automatic Protocol, Columns Experiments, Dynamic Automated Columns, Radial Column, Sorption Column)

- All five share a distinctive item-level formula not seen in Static boards: **`Active Sorbent Mass = ({sorbent_mass} * (1 - {humidity_factor}) * {sorbent_pct}) * 0.9`** — verbatim identical string across Automatic Protocol, Dynamic Automated Columns, and Radial Column. This is the Column family's equivalent of the Static family's per-formula sorbent-% handling, but centralized into one item-level formula that subitem formulas then reference (via mirror), rather than each subitem formula redoing the sorbent-% math itself.
- **Real bug found:** Dynamic Automated Columns' subitems board (5101219489) has its parent-link `board_relation` column (`board_relation_mm01ggmw`, titled "Column Automation Protocol") pointing at **boardIds: [5090899618]**, which is **Radial Column's board ID, not Dynamic Automated Columns' own** (5101219488). Its "Sorbent mass" and "Active Sorbent Mass" mirror columns read through that same wrong relation. This looks like the subitems schema was cloned from Radial Column and the self-reference was never repointed — anyone linking a subitem to its parent item today would be picking from Radial Column's item list, not Dynamic Automated Columns' own items. Worth confirming with the board owner and fixing before this board is used as a create-skill template.
- Columns Experiments⚗️ is structurally the richest of the five — item-level mirrors use `function: "sum"` (not "average" like every other board) to total subitem-level formula outputs, then item-level formulas divide those sums by total eluent volume to get true concentrations (`C, Li` etc.), then further formulas compute recovery rate (`α Li`) and selectivity ratios (`P (Li/Na)` etc.) — a longer formula chain than any other board. This board is likely the most mature/complete template for the Column category.
- Automatic Protocol Experiments, Radial Column, and (once its wrong-board bug is fixed) Dynamic Automated Columns are otherwise near-duplicates of each other's subitems formula sets (E,* / M-ratio / mass-ratio blocks are verbatim identical across all three).

## Sorption-category family (Sorption Beaker Board, Sorption Column)

- These two are **not near-duplicates of each other** — different apparatus, different metrics, unlike the Static trio. Beaker Board tracks `E, Li` and `Recovery Rate` per subitem-cycle with `function: "max"` mirrors (not average/sum) — i.e. it reports the *final* value reached, not an average across cycles, which fits a beaker experiment run to completion rather than repeated identical cycles. Sorption Column (see Q2 above) tracks bed-volumes and connects live to Brines DataBase.
- Sorption Beaker Board also connects to Brines DataBase directly (5 mirror columns, same pattern as Sorption Column) — so both Sorption-category boards connect live to brine data, unlike every Static/Automatic-Protocol board which hand-types it.

## 3-Sample Machine family (Meta Board, Cycle Data)

- Covered under Q3 above — three-tier hierarchy, still early-stage (Meta Board has only 1 item).

## Full connect/mirror map to Brines DataBase (1142444759) — corrected across all 12 boards

Connects directly: **Columns Experiments⚗️, Automatic Protocol Experiments🤖, Dynamic Automated Columns, Radial Column, Sorption Beaker Board, Sorption Column, Meta Board - 3 Sample Experiments** (all via `board_relation` column, several with paired mirror columns pulling Li/Na/K/Ca/Mg).
Does NOT connect (brine hand-typed or not tracked): **Static Granulated Lots, Static Ashkelon Lots, Static Mineral Lots, Pulsation Column Test Board, Cycle Data - 3 Sample Experiments** (Cycle Data pulls brine indirectly via its board_relation to Meta Board instead).

So the real pattern is: **Static-category boards never connect to Brines DataBase; every other category does.** This refines the doc's open Q4 — it's not "no board connects," it's specifically a Static-category convention (possibly because Static experiments predate the Brines DataBase board, or because Static lots don't track a single traceable brine batch the way column/sorption runs do — worth asking the owner which).

---

# Pass 3 — real item/subitem data sanity check

Pulled 2-3 real items + subitems each from Static Granulated Lots, Automatic Protocol Experiments, Columns Experiments⚗️, Sorption Column, and Cycle Data - 3 Sample Experiments to confirm the schema-only findings above hold in practice.

- **Confirms the schema is accurate**: formula outputs, board_relation links (e.g. Automatic Protocol and Sorption Column both correctly linking specific items to their Brines DataBase brine batch), and the 3-tier Meta Board → Cycle → Sample hierarchy all check out against live data.
- **Sorption Column's BV metric works as designed**: real sample data on item 2568259869 shows BV climbing 5.6 → 11.1 → 16.7 across samples 1-3, exactly the breakthrough-curve progression the schema implies.
- **Two "defined but unused in practice" columns found** — worth the audit treating these as a distinct category from drift/bugs, not flagging as errors:
  - Sorption Column's subitem `pH` field is empty on every sample checked, despite being in the schema.
  - Cycle Data - 3 Sample Experiments' `Sorption Li Capacity` formula is empty on every sample because its input (`Sorption Li (ppm)`) is never filled in practice.
