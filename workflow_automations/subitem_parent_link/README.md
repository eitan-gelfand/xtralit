# Subitem → Parent Link (monday app)

Adds an automation recipe to the board's **Automations** center:

> **When a subitem is created, connect it to its parent item**

It fills the subitems board's Connect Boards column (the one that links to the parent board),
so mirror and formula columns on the subitem work without anyone linking by hand.
Built for board 5101266880, but it works on any board where the recipe is added.

The Connect column is found automatically: it's the `board_relation` column on the subitems
board whose linked board is the parent board. Existing links are kept; the parent is added.

## Files
- `main.py`: Flask routes (subscribe / unsubscribe / board webhook / action)
- `monday_api.py`: GraphQL calls
- `auth.py`: verifies monday's JWT and signs trigger calls

## 1. Create the app (monday Developer Center)
1. Avatar → **Developers** → **Create app**. Name it `Subitem Parent Link`.
2. **Basic information**: copy the **App ID** and the **Signing Secret**.
3. **OAuth & Permissions → Scopes**: tick `boards:read`, `boards:write` and `webhooks:write`.

## 2. Deploy to monday code
```bash
npm i -g @mondaycom/apps-cli
mapps init                      # paste a developer API token when asked
cd workflow_automations/subitem_parent_link
mapps code:push                 # choose the app; prints the URL, e.g. https://xxxx.monday.app
mapps code:env -m set -k MONDAY_SIGNING_SECRET -v <signing secret>
mapps code:env -m set -k MONDAY_APP_ID -v <app id>
mapps code:env -m set -k APP_BASE_URL -v https://xxxx.monday.app
mapps code:push                 # redeploy so the env vars are picked up
```
Opening `https://xxxx.monday.app/` should show `ok`.

## 3. Add the recipe (Developer Center → app → Features)
1. **Create feature → Integration for sentence builder**. Base URL: `https://xxxx.monday.app`.
2. **Workflow blocks → Create trigger** (custom):
   - Name `Subitem created`
   - Input field: key `boardId`, type **Board** (source: context)
   - Output field: key `subitemId`, type **Number**
   - Subscribe URL `/trigger/subscribe`, Unsubscribe URL `/trigger/unsubscribe`
3. **Workflow blocks → Create action** (custom):
   - Name `Connect subitem to parent`
   - Input field: key `subitemId`, type **Number**
   - Run URL `/action/connect-parent`
4. **Recipes → Create recipe**, trigger `Subitem created`, action `Connect subitem to parent`
   - Sentence: `When a subitem is created, connect it to its parent item`
   - Map trigger input `boardId` ← context board; map action input `subitemId` ← trigger
     output `subitemId`.
5. **Promote to live** / create a version, then **Install** the app in the account.

## 4. Use it
Board → **Automate** → search the app (or **Apps** tab) → add the recipe. That's it.

## Debugging
`mapps code:logs` shows every call (`Subscribed board…`, `Subitem … created`, `Connected …`).
Subscribing creates a `create_subitem` webhook on the board; deleting the recipe removes it.
