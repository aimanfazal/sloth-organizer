# 🦥 Sloth Organizer — Implementation Plan

## Top-Level Overview

**Goal:** Build the Sloth Organizer MVP — a local-first AI application that scans a messy folder,
uses a locally-running open-weight model (via LM Studio) to propose an organization plan, and
applies approved file moves/renames safely after human review.

**Scope:**
- Python + FastAPI backend (serves API and React static build)
- React + Vite frontend (compiled to `dist/`, served by FastAPI)
- SQLite persistence for scans and plans
- WebSocket for real-time scan progress
- LM Studio OpenAI-compatible API for local AI inference
- Packaged as a single `pip`-installable package

**Approach:** Build in layers — project scaffold first, then data layer, then backend domain
modules (scan → AI → file ops), then frontend screens in flow order, then integration and packaging.

**Non-goals (MVP):** Deletion, undo/rollback, cloud sync, accounts, auth, OCR, image understanding,
mobile, multi-agent, vector DB, integrations.

---

## Sub-Tasks

---

### Sub-Task 1 — Project Scaffold

**Status:** `[x] done`

**Intent:**
Establish the monorepo layout, tooling config, and entry points for both backend and frontend
so that every subsequent sub-task has a stable place to land.

**Expected Outcomes:**
- `backend/` Python package with `pyproject.toml`, FastAPI app skeleton, and a `main.py` entry point
- `frontend/` Vite + React + TypeScript project with placeholder `App.tsx`
- `backend/` serves `frontend/dist/` as static files at `/`
- Running `uvicorn sloth_organizer.main:app` starts the server
- `pip install -e .` installs the package and exposes a `sloth-organizer` CLI command

**Todo List:**
1. Create `backend/sloth_organizer/` Python package with `__init__.py` and `main.py`
2. Create `pyproject.toml` at root with `[project]`, `[project.scripts]` (CLI entry point), and dependencies (`fastapi`, `uvicorn`, `sqlmodel`, `aiofiles`, `websockets`, `pypdf`, `python-docx`, `openpyxl`, `openai`, `python-magic-bin` or `python-magic`)
3. Create `backend/sloth_organizer/main.py` — FastAPI app that mounts `StaticFiles` from `../frontend/dist` and includes API routers
4. Create `frontend/` via Vite (`npm create vite@latest frontend -- --template react-ts`)
5. Add `frontend/.env.example` with `VITE_API_BASE_URL=http://localhost:8000`
6. Add root `README.md` with setup instructions (install Python deps, build frontend, run server)

**Relevant Context:**
- FastAPI `StaticFiles` mount: serve `frontend/dist` at `/`, API routes under `/api`
- CLI entry point in `pyproject.toml`: `sloth-organizer = "sloth_organizer.main:run"`
- `run()` calls `uvicorn.run("sloth_organizer.main:app", ...)`

---

### Sub-Task 2 — SQLite Data Layer

**Status:** `[x] done`

**Intent:**
Define the database schema and ORM models for scans, files, plans, and plan items so that
all backend modules share a single, typed data layer with persistent state across restarts.

**Expected Outcomes:**
- SQLite database created at a configurable path (default `~/.sloth_organizer/data.db`)
- Tables: `scans`, `files`, `plans`, `plan_items`
- All models defined using `SQLModel` (combines Pydantic + SQLAlchemy)
- Database initialized on app startup

**Todo List:**
1. Create `backend/sloth_organizer/database.py` — engine creation, `init_db()`, `get_session()` dependency
2. Create `backend/sloth_organizer/models.py` — define the following `SQLModel` table models:
   - `Scan`: `id` (str, PK), `folder_path` (str), `status` (str), `file_count` (int), `duplicate_groups` (int), `total_size_bytes` (int), `created_at` (datetime)
   - `ScannedFile`: `id` (str, PK), `scan_id` (str, FK), `filename` (str), `relative_path` (str), `extension` (str), `size_bytes` (int), `created_at` (datetime), `modified_at` (datetime), `mime_type` (str), `sha256` (str), `content_preview` (str | None), `is_duplicate` (bool)
   - `Plan`: `id` (str, PK), `scan_id` (str, FK), `summary` (str), `status` (str), `created_at` (datetime)
   - `PlanItem`: `id` (str, PK), `plan_id` (str, FK), `file_id` (str, FK), `source_path` (str), `destination` (str), `new_name` (str | None), `reason` (str), `task` (str | None), `priority` (str | None), `confidence` (float), `approved` (bool | None), `applied` (bool)
3. Call `init_db()` in the FastAPI `lifespan` startup handler in `main.py`

**Relevant Context:**
- `SQLModel` docs: https://sqlmodel.tiangolo.com
- Use `uuid4()` strings as PKs for portability
- `approved = None` means unreviewed; `True` = approved; `False` = rejected

---

### Sub-Task 3 — File Scanner (Backend)

**Status:** `[x] done`

**Intent:**
Implement the core filesystem scanning logic: recursive directory walk, metadata collection,
SHA-256 hashing, MIME type detection, content preview extraction, and duplicate detection.
This is the first heavy domain module and must be correct before the AI layer is built.

**Expected Outcomes:**
- `POST /api/scan` accepts `{"folder": "/abs/path"}` and returns `{"scan_id": "...", "file_count": N, "duplicate_groups": M}`
- Scan runs synchronously in a background task; progress is broadcast over WebSocket
- `GET /api/scans/{scan_id}/files` returns the list of `ScannedFile` records
- Content previews extracted for: `.txt`, `.md`, `.csv`, `.json`, `.pdf`, `.docx`, `.xlsx`
- SHA-256 computed for every file; duplicate groups identified by matching hashes
- Scan state stored in SQLite

**Todo List:**
1. Create `backend/sloth_organizer/scanner.py`:
   - `scan_folder(folder_path, scan_id, session, progress_callback)` — async generator or function
   - Recursive walk using `pathlib.Path.rglob("*")`
   - For each file: collect `filename`, `relative_path`, `extension`, `size_bytes`, `created_at`, `modified_at`
   - MIME type detection via `python-magic` (fallback: `mimetypes` stdlib)
   - SHA-256 using `hashlib` with chunked reads
   - Content preview extraction (max 500 chars) for supported extensions
   - Call `progress_callback(percent, stage_label)` at milestones
2. Create `backend/sloth_organizer/extractors.py`:
   - `extract_preview(path, extension) -> str | None`
   - `.txt`, `.md`, `.csv`, `.json` — read first 500 chars
   - `.pdf` — `pypdf` first page text, truncated
   - `.docx` — `python-docx` first paragraph(s), truncated
   - `.xlsx` — `openpyxl` first sheet cell values, truncated
3. Create `backend/sloth_organizer/routers/scan.py`:
   - `POST /api/scan` — create `Scan` record, launch background scan task, return `scan_id`
   - `GET /api/scans/{scan_id}` — return scan status and summary counts
   - `GET /api/scans/{scan_id}/files` — return paginated list of `ScannedFile`
4. Create `backend/sloth_organizer/ws.py`:
   - WebSocket manager: `connect(scan_id, ws)`, `disconnect(scan_id, ws)`, `broadcast(scan_id, message)`
   - `WS /ws/scan/{scan_id}` endpoint
5. Wire progress broadcasts from scanner into WebSocket manager during scan execution

**Relevant Context:**
- `python-magic` requires `libmagic`; on Windows use `python-magic-bin` instead
- Content previews are sent to the AI later — keep them under 500 chars to control token usage
- Duplicate groups: group `ScannedFile` records by `sha256`; any group with count > 1 is a duplicate group

---

### Sub-Task 4 — LM Studio AI Integration (Backend)

**Status:** `[x] done`

**Intent:**
Implement the context builder and AI client that takes scanned file metadata, constructs a
compact prompt, calls LM Studio's OpenAI-compatible API, validates the JSON response, and
stores the resulting organization plan in SQLite.

**Expected Outcomes:**
- `POST /api/scans/{scan_id}/plan` triggers AI inference and returns `{"plan_id": "...", "summary": "...", "items": [...]}`
- Context builder produces a compact JSON representation of all scanned files
- Response is validated against the expected schema; retried once on failure; error surfaced if retry also fails
- `Plan` and `PlanItem` records written to SQLite
- LM Studio base URL and model name configurable via environment variables

**Todo List:**
1. Create `backend/sloth_organizer/config.py`:
   - Pydantic `Settings` class: `LM_STUDIO_BASE_URL` (default `http://127.0.0.1:1234/v1`), `LM_STUDIO_MODEL` (default `""`), `DB_PATH` (default `~/.sloth_organizer/data.db`)
   - Loaded via `pydantic-settings` from environment / `.env` file
2. Create `backend/sloth_organizer/ai_client.py`:
   - `check_lm_studio() -> bool` — GET `{base_url}/models`, return True if reachable
   - `build_context(files: list[ScannedFile]) -> str` — serialize files as compact JSON array
   - `build_prompt(context: str) -> str` — system + user prompt instructing the model to return the schema from Section 8 of mvp.md; include organization rules from Section 9
   - `generate_plan(files) -> dict` — call LM Studio chat completions, parse JSON from response, retry once on failure, raise on second failure
3. Create `backend/sloth_organizer/routers/plan.py`:
   - `POST /api/scans/{scan_id}/plan` — load files from DB, call `generate_plan`, validate response, write `Plan` + `PlanItem` records, return plan
   - `GET /api/plans/{plan_id}` — return plan with all items
   - `PATCH /api/plans/{plan_id}/items/{item_id}` — update `approved` field (True/False) for human review
4. Add `GET /api/lm-studio/status` endpoint that calls `check_lm_studio()` and returns `{"connected": bool, "model": str | None}`

**Relevant Context:**
- Use the `openai` Python SDK pointed at LM Studio base URL — it is OpenAI-compatible
- Priority values from AI: normalize to `"high"`, `"medium"`, `"low"` (drop `"critical"`, fold into `"high"`)
- Prompt must instruct the model to return **only** valid JSON matching the schema — no markdown fences, no prose
- `confidence` must be float 0–1; `destination` must be a folder name string (not a path)

---

### Sub-Task 5 — Safe File Executor (Backend)

**Status:** `[ ] pending`

**Intent:**
Implement the plan executor that applies approved file moves and renames safely, following
the 10-step safety model from Section 25 of mvp.md. This module must never delete, overwrite,
or touch unapproved items.

**Expected Outcomes:**
- `POST /api/plans/{plan_id}/apply` accepts `{"approved_items": [...], "dry_run": false}` and executes only approved items
- Dry-run returns what would happen without touching the filesystem
- Files are moved/renamed atomically; destination folders are created as needed
- Name collision resolved by appending `(2)`, `(3)` etc. — never silent overwrite
- Each item's `applied` field updated in SQLite after execution
- Returns `{"moved": N, "renamed": N, "skipped": N, "errors": [...]}`

**Todo List:**
1. Create `backend/sloth_organizer/executor.py`:
   - `resolve_destination(root, destination_folder, new_name, original_name) -> Path` — builds the target path, stays inside root, sanitizes folder/filename
   - `prevent_overwrite(path: Path) -> Path` — appends `(2)`, `(3)` etc. if target exists
   - `validate_item(root, item: PlanItem) -> None` — runs all 10 safety checks from Section 25: source exists, source inside root, destination inside root, no path traversal, no overwrite
   - `execute_item(root, item: PlanItem, dry_run: bool) -> dict` — calls validate, creates destination folder, moves file (or simulates if dry_run)
2. Create `backend/sloth_organizer/routers/apply.py`:
   - `POST /api/plans/{plan_id}/apply` — load plan, filter to `approved_items`, call `execute_item` for each, update `applied` in DB, return summary

**Relevant Context:**
- `root` is the original `Scan.folder_path` — all paths must be resolved relative to this
- Use `pathlib.Path.resolve()` to detect path traversal: check `resolved_path.is_relative_to(resolved_root)`
- `shutil.move()` for actual file operations
- Never touch items where `approved != True`

---

### Sub-Task 6 — Frontend: Home + LM Studio Status (Screen 1)

**Status:** `[ ] pending`

**Intent:**
Build the Home screen — the entry point of the app. It must check LM Studio connectivity at
load time, show a status badge, accept a folder path input, and navigate to the Scan screen.

**Expected Outcomes:**
- Home screen renders at `/`
- LM Studio status checked via `GET /api/lm-studio/status` on mount; badge shows ✅ or ⚠️
- Folder path text input; "Select Folder" button navigates to `/scan` and triggers scan
- Scan is blocked (button disabled + tooltip) if LM Studio is not connected

**Todo List:**
1. Set up React Router in `frontend/src/main.tsx` with routes: `/`, `/scan`, `/organize`, `/tasks`, `/review`, `/apply`
2. Create `frontend/src/api/client.ts` — typed fetch wrappers for all backend endpoints and WebSocket helper
3. Create `frontend/src/pages/Home.tsx`:
   - On mount: call `GET /api/lm-studio/status`, set status state
   - Render: app title, tagline, folder path `<input>`, "Select Folder" button, LM Studio status badge
   - On submit: `POST /api/scan`, navigate to `/scan?scan_id=...`
4. Create `frontend/src/components/LmStudioBadge.tsx` — reusable status badge component

**Relevant Context:**
- Screen 1 mockup in Section 19 of mvp.md
- Folder path is a plain text input — no native file picker (browser security limitation)
- Tailwind CSS recommended for styling; add via `npm install -D tailwindcss`

---

### Sub-Task 7 — Frontend: Scan Progress (Screen 2)

**Status:** `[ ] pending`

**Intent:**
Build the Scan screen that connects to the backend WebSocket and shows live progress: percent
complete, current stage label, and the final summary counts when the scan finishes.

**Expected Outcomes:**
- Connects to `WS /ws/scan/{scan_id}` immediately on mount
- Progress bar updates in real time from WebSocket messages
- Stage labels displayed: "Finding files…", "Reading metadata…", "Detecting duplicates…", "Preparing AI context…"
- On scan complete: shows `N files / N folders / N duplicate groups / X GB`
- "Continue →" button appears on completion, navigates to `/organize`

**Todo List:**
1. Create `frontend/src/pages/Scan.tsx`:
   - Read `scan_id` from URL query param
   - Open WebSocket connection to `WS /ws/scan/{scan_id}` on mount; close on unmount
   - Handle WebSocket messages: `{type: "progress", percent: N, stage: "..."}` and `{type: "complete", summary: {...}}`
   - Render progress bar + stage label during scan; summary card + Continue button on completion
2. Define WebSocket message shape in `frontend/src/api/types.ts`

**Relevant Context:**
- Screen 2 mockup in Section 20 of mvp.md
- WebSocket should reconnect once if it drops unexpectedly during scan

---

### Sub-Task 8 — Frontend: AI Organization Summary (Screen 3)

**Status:** `[ ] pending`

**Intent:**
Build the AI Organization screen that triggers plan generation (calls `POST /api/scans/{scan_id}/plan`),
shows a loading state while the model runs, and then displays the folder breakdown summary.

**Expected Outcomes:**
- On mount: automatically calls `POST /api/scans/{scan_id}/plan`
- Loading state shown while waiting for model response (can take seconds to minutes)
- On success: shows the AI summary text and folder breakdown table (`Projects 23 files`, etc.)
- On error (after retry): shows error message with retry button
- "View Tasks →" button navigates to `/tasks`

**Todo List:**
1. Create `frontend/src/pages/Organize.tsx`:
   - On mount: call `POST /api/scans/{scan_id}/plan`, store `plan_id`
   - Loading: spinner + "Sloth is thinking…" message
   - Success: render `plan.summary` and folder breakdown from `plan.items` (group by `destination`, count files)
   - Error: error card with retry button
2. Store `plan_id` in component state and pass via navigation or URL param to subsequent screens

**Relevant Context:**
- Screen 3 mockup in Section 21 of mvp.md
- Plan generation can be slow (model inference); loading state UX is important

---

### Sub-Task 9 — Frontend: Tasks Dashboard (Screen 4)

**Status:** `[ ] pending`

**Intent:**
Build the Tasks screen that surfaces only the files requiring human action, grouped by priority
(High → Medium → Low), with a link from each task to its associated file in the Review screen.

**Expected Outcomes:**
- Shows only `PlanItem` records where `task != null`, grouped by `priority`
- Priority sections rendered in order: 🔥 High → 🟡 Medium → 🟢 Low
- Each task shows the task text; clicking it highlights the corresponding file in the Review screen
- "Review All Changes →" button navigates to `/review`

**Todo List:**
1. Create `frontend/src/pages/Tasks.tsx`:
   - Load plan items from `GET /api/plans/{plan_id}` (already fetched; can pass via state or re-fetch)
   - Filter items where `task !== null`
   - Group by `priority` (`high`, `medium`, `low`)
   - Render priority sections with appropriate icons and task text
   - Each task is a link that navigates to `/review?highlight={item_id}`

**Relevant Context:**
- Screen 4 mockup in Section 22 of mvp.md
- Only 3 priority tiers: `high`, `medium`, `low` (no `critical`)

---

### Sub-Task 10 — Frontend: Review Screen (Screen 5)

**Status:** `[ ] pending`

**Intent:**
Build the Review screen where the user approves or rejects each proposed file change.
Each file appears as a card showing source, destination, rename, reason, confidence, and task.
Approval state is persisted to the backend immediately.

**Expected Outcomes:**
- All `PlanItem` records shown as cards, one per file
- Each card shows: original path, destination folder, new name (if any), reason, confidence %, task (if any), priority badge (if any)
- Approve / Reject buttons on each card; state saved via `PATCH /api/plans/{plan_id}/items/{item_id}`
- Cards highlighted when navigated to via task link (using URL `?highlight` param)
- "Continue to Apply →" button (enabled only if at least one item approved) navigates to `/apply`

**Todo List:**
1. Create `frontend/src/pages/Review.tsx`:
   - Load all plan items from `GET /api/plans/{plan_id}`
   - Render each as a `<FileCard>` component
   - On Approve/Reject: call `PATCH /api/plans/{plan_id}/items/{item_id}` with `{approved: true/false}`; update local state optimistically
   - Scroll to and highlight item if `?highlight={item_id}` is in URL
2. Create `frontend/src/components/FileCard.tsx` — card UI for a single plan item

**Relevant Context:**
- Screen 5 mockup in Section 23 of mvp.md
- Confidence displayed as percentage: `(confidence * 100).toFixed(0) + "%"`

---

### Sub-Task 11 — Frontend: Apply Screen (Screen 6)

**Status:** `[ ] pending`

**Intent:**
Build the Apply screen that shows a final summary of approved changes, supports dry-run preview,
and executes the plan on user confirmation. Shows per-item results after execution.

**Expected Outcomes:**
- Shows count of files to move, rename, skip (unapproved), and confirms 0 deletions
- "← Review Changes" back button
- "🦥 Apply Changes" button calls `POST /api/plans/{plan_id}/apply` with `dry_run: false`
- Execution results displayed: moved N, renamed N, skipped N, any errors listed
- No undo UI — changes are permanent

**Todo List:**
1. Create `frontend/src/pages/Apply.tsx`:
   - Load approved items count from plan state
   - Render pre-apply summary card (moves, renames, 0 deletes)
   - On "Apply Changes": call `POST /api/plans/{plan_id}/apply` with `{"approved_items": [...approved_ids], "dry_run": false}`, show loading state
   - On success: render results card with moved/renamed/skipped counts and any errors
   - No undo option — show a note: "Files were moved, not deleted. You can move them back manually."

**Relevant Context:**
- Screen 6 mockup in Section 24 of mvp.md
- Approved item IDs must be passed — collect from plan items where `approved === true`

---

### Sub-Task 12 — Packaging & README

**Status:** `[ ] pending`

**Intent:**
Wire everything together into a single installable pip package: build script that compiles the
React frontend into `dist/`, bundles it inside the Python package, and exposes a `sloth-organizer`
CLI command that starts the server.

**Expected Outcomes:**
- `pip install -e .` installs all dependencies
- `sloth-organizer` CLI command starts FastAPI + serves the React app at `http://localhost:8000`
- `README.md` covers: prerequisites (Python 3.11+, Node 18+, LM Studio), install steps, run steps
- `.env.example` documents `LM_STUDIO_BASE_URL`, `LM_STUDIO_MODEL`, `DB_PATH`

**Todo List:**
1. Update `pyproject.toml` to include `frontend/dist/` in package data (via `[tool.setuptools.package-data]`)
2. Add `build.sh` / `build.ps1` script: `cd frontend && npm install && npm run build`, then copies `dist/` into `backend/sloth_organizer/static/`
3. Update `main.py` StaticFiles mount to point to the bundled `static/` folder inside the package
4. Write `README.md`: prerequisites, `git clone`, `pip install -e .`, build frontend, set `.env`, run `sloth-organizer`
5. Write `.env.example` with all config keys and their defaults

**Relevant Context:**
- `importlib.resources` or `__file__`-relative path can locate the bundled `static/` folder at runtime
- FastAPI `StaticFiles(directory=..., html=True)` enables SPA fallback routing

---

## Architecture Diagram

```
User Browser
    │  HTTP / WS
    ▼
FastAPI (serves /api/* + static React build at /)
    │
    ├── POST /api/scan ──────────► scanner.py ──► SQLite (scans, files)
    │                                   │
    │                              WS broadcast
    │                                   ▼
    │                           WS /ws/scan/{id}
    │
    ├── POST /api/scans/{id}/plan ► ai_client.py ──► LM Studio (localhost:1234)
    │                                   │
    │                              SQLite (plans, plan_items)
    │
    ├── PATCH /api/plans/{id}/items/{id} ► update approved in SQLite
    │
    └── POST /api/plans/{id}/apply ──► executor.py ──► Local Filesystem
                                            │
                                       SQLite (applied=true)
```

---

## Implementation Order

Sub-tasks are ordered by dependency:

1. **Scaffold** → establishes structure
2. **Data Layer** → required by all backend modules
3. **Scanner** → produces data that AI and executor need
4. **AI Integration** → depends on scanned file data
5. **Safe Executor** → depends on AI plan data
6–11. **Frontend screens** → built in user-flow order (Home → Scan → Organize → Tasks → Review → Apply)
12. **Packaging** → final integration step
