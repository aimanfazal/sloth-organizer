# 🦥 Sloth Organizer — MVP

## 1. Product Overview

**Sloth Organizer** is a local-first AI application that turns a messy folder into an organized workspace.

The user selects a folder. Sloth Organizer analyzes its files using:

- Filenames
- File extensions
- File size
- Created/modified timestamps
- MIME type
- File hashes
- Lightweight document content

A locally running open-weight model analyzes this information and proposes:

1. Where each file should go
2. A better filename when appropriate
3. A short task if the file requires human action
4. A priority for that task
5. A confidence score

The user reviews the recommendations and approves the changes before anything is moved.

### Core philosophy

> **Don't make the user work faster. Make the user have less work to do.**

---

# 2. MVP Goal

The MVP should answer one question:

> **Can a local AI look at a messy folder and safely turn it into a much more manageable workspace?**

The MVP flow is:

```text
Scan
  ↓
Understand
  ↓
Organize
  ↓
Create tasks
  ↓
Prioritize
  ↓
Review
  ↓
Apply
```

The MVP is intentionally not an autonomous file-management agent.

---

# 3. Target User

The initial target user is anyone with a messy:

- Downloads folder
- Desktop
- Documents folder
- Project folder
- Research folder
- Freelance/work folder

Especially:

- Developers
- Students
- Freelancers
- Researchers
- Knowledge workers

---

# 4. Core User Flow

## Step 1 — Select a folder

The user selects a local folder.

Example:

```text
~/Downloads
```

The application must never upload the folder itself.

---

## Step 2 — Scan

The backend recursively scans the folder.

For every file, collect:

```text
filename
relative path
extension
size
created_at
modified_at
MIME type
SHA-256
content preview
```

Content previews are extracted only for supported formats.

Initial formats:

```text
.txt
.md
.csv
.json
.pdf
.docx
.xlsx
```

Additional formats can be added later.

---

# 5. File Understanding

The application should send a **compact representation** of each file to the local model.

Example:

```json
{
  "path": "Downloads/project-proposal-v7.pdf",
  "name": "project-proposal-v7.pdf",
  "extension": ".pdf",
  "size_bytes": 182930,
  "modified_at": "2026-10-18T14:20:31",
  "mime_type": "application/pdf",
  "content_preview": "Project proposal for website redesign..."
}
```

The application should avoid sending entire files to the model.

The goal is:

> **Give the model enough information to make a useful decision, but no more than necessary.**

---

# 6. Local AI

## LM Studio

The MVP uses **LM Studio** as the local model runtime.

The user starts LM Studio and loads an open-weight model.

The application communicates with LM Studio through its local OpenAI-compatible API.

Example configuration:

```text
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
LM_STUDIO_MODEL=<loaded-model>
```

The exact model is configurable.

The MVP should not hard-code the application to one model.

Potential models can include compatible open-weight instruction models such as:

```text
Qwen
Llama
Mistral
Gemma
```

The model choice should ultimately depend on the user's hardware.

---

# 7. AI Responsibilities

The model is responsible for **reasoning about organization**.

It should determine:

### Destination

Example:

```text
invoice.pdf
    ↓
Finance/
```

### Filename

Example:

```text
final_project_v7.pdf
    ↓
Website_Redesign_Proposal.pdf
```

### Task

Example:

```text
Pay October invoice
```

### Priority

Example:

```text
HIGH
```

### Confidence

Example:

```text
0.91
```

The model should return structured JSON.

---

# 8. AI Output Schema

The backend should expect something similar to:

```json
{
  "summary": "This folder contains project documents, financial files, personal documents and several files requiring review.",
  "folders": [
    "Projects",
    "Finance",
    "Personal",
    "Review"
  ],
  "items": [
    {
      "path": "project-proposal-v7.pdf",
      "destination": "Projects",
      "new_name": "Website_Redesign_Proposal.pdf",
      "reason": "The document appears to be a project proposal.",
      "task": null,
      "priority": null,
      "confidence": 0.94
    },
    {
      "path": "invoice_oct.pdf",
      "destination": "Finance",
      "new_name": "Invoice_October_2026.pdf",
      "reason": "The document appears to be an invoice.",
      "task": "Pay October invoice",
      "priority": "high",
      "confidence": 0.91
    }
  ]
}
```

The backend must validate this response before showing it to the user.

---

# 9. Organization Rules

The model should follow conservative rules.

## Never delete

The MVP must never automatically delete files.

Duplicates can be identified, but deletion is always a future feature.

## Prefer existing folders

If the folder already contains:

```text
Projects/
Finance/
```

the model should use those folders rather than inventing alternatives.

## Avoid folder explosion

Don't create:

```text
Documents/
Documents/Important/
Documents/Important/Projects/
Documents/Important/Projects/Current/
```

Prefer a simple structure:

```text
Projects/
Finance/
Personal/
Review/
```

## Preserve extensions

```text
report.pdf
```

can become:

```text
Annual_Report_2026.pdf
```

but never:

```text
Annual_Report_2026
```

## Don't guess

If confidence is low:

```text
destination = Review
```

---

# 10. Task Generation

Sloth Organizer should identify files that appear to require human action.

Tasks must be short and actionable.

### Good

```text
Pay October invoice
```

```text
Review client contract
```

```text
Finish project proposal
```

```text
Check duplicate report
```

### Bad

```text
You should probably review this document and determine whether
the contents are still relevant before deciding what to do with it.
```

The application should make the user's workload smaller, not create more AI-generated busywork.

---

# 11. Priority System

Each task receives one priority.

## Critical

Time-sensitive or potentially consequential.

Examples:

```text
Pay overdue invoice
Renew expiring document
Submit application
```

## High

Important but not necessarily urgent.

Examples:

```text
Review contract
Reply to client
Finish project proposal
```

## Medium

Useful but not urgent.

Examples:

```text
Review old report
Organize research notes
Rename project files
```

## Low

Optional cleanup.

Examples:

```text
Archive old screenshots
Rename miscellaneous images
Review old duplicates
```

---

# 12. Duplicate Detection

Duplicate detection happens locally using SHA-256.

Example:

```text
invoice.pdf
invoice_copy.pdf
invoice_old.pdf
```

If all three have the same hash:

```text
♻️ Duplicate group

3 identical files found.

Keep:
invoice.pdf

Review:
invoice_copy.pdf
invoice_old.pdf
```

The MVP must **never delete duplicates automatically**.

---

# 13. Human-in-the-Loop

AI recommendations must never immediately modify the filesystem.

Every recommendation should be reviewable.

Example UI:

```text
┌─────────────────────────────────────────────┐
│ invoice_oct.pdf                             │
│                                             │
│ → Finance/Invoice_October_2026.pdf          │
│                                             │
│ 📝 Pay October invoice                      │
│ 🔥 HIGH                                     │
│                                             │
│ Confidence: 91%                             │
│                                             │
│ ☑ Approve                                   │
└─────────────────────────────────────────────┘
```

The user can approve or reject individual changes.

---

# 14. Dry Run

Dry-run mode is enabled by default.

When enabled:

```text
No files will be changed.
```

The user sees:

```text
12 files will be moved
4 files will be renamed
3 files require review
2 duplicate groups detected
```

Only after explicitly disabling dry-run can the user apply changes.

---

# 15. Safe File Operations

The MVP can:

- Create folders
- Move files
- Rename files

The MVP cannot:

- Delete files
- Overwrite files
- Modify document contents
- Execute arbitrary commands
- Upload files

If a destination already exists:

```text
report.pdf
report (2).pdf
report (3).pdf
```

The application must never silently overwrite the existing file.

---

# 16. Architecture

```text
                     USER'S MACHINE
┌───────────────────────────────────────────────────┐
│                                                   │
│                 Web Browser                      │
│                     │                             │
│                     ▼                             │
│             React / Next.js UI                   │
│                     │                             │
│              HTTP / WebSocket                    │
│                     │                             │
│                     ▼                             │
│              FastAPI Backend                     │
│                     │                             │
│          ┌──────────┼──────────┐                 │
│          ▼          ▼          ▼                 │
│      File Scan   Metadata   Content             │
│                              Extractor            │
│          │          │          │                 │
│          └──────────┼──────────┘                 │
│                     ▼                             │
│              Context Builder                     │
│                     │                             │
│                     ▼                             │
│              LM Studio API                       │
│                     │                             │
│                     ▼                             │
│             Open-Weight Model                    │
│                     │                             │
│                     ▼                             │
│               JSON Plan                          │
│                     │                             │
│                     ▼                             │
│              Human Review                       │
│                     │                             │
│                     ▼                             │
│             Safe Executor                        │
│                     │                             │
│                     ▼                             │
│              Local Files                         │
│                                                   │
└───────────────────────────────────────────────────┘
```

---

# 17. Recommended Technology Stack

## Frontend

**React + TypeScript**

Responsibilities:

- Folder selection
- Scan progress
- File overview
- Organization recommendations
- Task dashboard
- Approval controls
- Dry-run interface
- Execution results

---

## Backend

**Python + FastAPI**

Responsibilities:

- Filesystem scanning
- Metadata extraction
- Hashing
- Document extraction
- LM Studio communication
- AI response validation
- Plan generation
- Safe file operations

---

## AI Runtime

**LM Studio**

Local OpenAI-compatible API.

Default:

```text
http://127.0.0.1:1234/v1
```

The model is configurable.

---

## Document Processing

Use lightweight Python libraries:

```text
pypdf
python-docx
openpyxl
```

---

# 18. Backend API

The MVP backend should expose a small API.

## Scan

```http
POST /api/scan
```

Request:

```json
{
  "folder": "/Users/me/Downloads"
}
```

Response:

```json
{
  "scan_id": "abc123",
  "file_count": 87,
  "duplicate_groups": 4
}
```

---

## Get Files

```http
GET /api/scans/{scan_id}/files
```

Returns scanned file metadata.

---

## Generate Plan

```http
POST /api/scans/{scan_id}/plan
```

The backend sends the compact file representation to LM Studio.

Response:

```json
{
  "plan_id": "plan123",
  "summary": "...",
  "items": []
}
```

---

## Apply Plan

```http
POST /api/plans/{plan_id}/apply
```

Request:

```json
{
  "approved_items": [
    "item_1",
    "item_4",
    "item_7"
  ],
  "dry_run": false
}
```

Response:

```json
{
  "moved": 7,
  "renamed": 3,
  "skipped": 1,
  "errors": []
}
```

---

# 19. Frontend Screens

## Screen 1 — Home

```text
🦥 Sloth Organizer

Give your messy folder to the sloth.

[ Select Folder ]

Your files stay on your machine.
AI runs locally through LM Studio.
```

---

# 20. Screen 2 — Scan

```text
Scanning Downloads...

██████████████████░░ 84%

Finding files...
Reading metadata...
Detecting duplicates...
Preparing AI context...
```

When complete:

```text
87 files
12 folders
4 duplicate groups
1.4 GB
```

---

# 21. Screen 3 — AI Organization

```text
🧠 Sloth's Plan

I found 87 files.

Most can be organized automatically.

I found 5 things that actually need your attention.
```

Then show:

```text
Projects       23 files
Finance        14 files
Documents      31 files
Media          11 files
Review          8 files
```

---

# 22. Screen 4 — Tasks

The task view should focus on reducing mental load.

```text
🦥 Your actual workload

5 things need you.

🔥 HIGH

Pay October invoice
Review client contract

🟡 MEDIUM

Finish project proposal
Review old report

🟢 LOW

Archive screenshots
```

The user should be able to click a task and see the associated file.

---

# 23. Screen 5 — Review

Each proposed change appears as a card.

```text
project-proposal-v7.pdf

Move to:
Projects/

Rename:
Website_Redesign_Proposal.pdf

Reason:
Looks like a project proposal.

Confidence:
94%

[ Approve ] [ Reject ]
```

---

# 24. Screen 6 — Apply

Before changing anything:

```text
Ready to organize?

12 files will move.
4 files will be renamed.
0 files will be deleted.

[ ← Review Changes ]

[ 🦥 Apply Changes ]
```

---

# 25. Safety Model

The application should treat AI output as **untrusted input**.

Before applying any action:

1. Validate the JSON.
2. Verify the source file exists.
3. Resolve the source path.
4. Verify it remains inside the selected root.
5. Sanitize the destination.
6. Prevent path traversal.
7. Prevent overwrites.
8. Verify the destination.
9. Perform the move.
10. Report the result.

The model should never be allowed to execute filesystem commands directly.

---

# 26. Privacy Model

The core promise:

> **Your files stay on your computer.**

The MVP should not:

- Upload files
- Call cloud AI APIs
- Send telemetry containing file contents
- Store documents remotely
- Require an account

The only AI communication is:

```text
FastAPI
   ↓
LM Studio
   ↓
Local model
```

All on the user's machine.

---

# 27. Offline Behavior

Once the model is downloaded into LM Studio, the core application should work without internet access.

```text
Internet
   ❌

LM Studio
   ↓
Local Model
   ↓
Sloth Organizer
   ↓
Local Files
```

This is one of the strongest reasons for using open-weight AI.

---

# 28. Open Innovation

Open AI is fundamental to the application rather than decorative.

The application deals with potentially sensitive personal files.

A cloud AI architecture would require the user to trust another service with those files.

The local architecture changes the tradeoff:

```text
Closed API

Private Files
      ↓
Internet
      ↓
Third-party AI
      ↓
Organization
```

versus:

```text
Open-weight AI

Private Files
      ↓
Local Application
      ↓
Local Model
      ↓
Organization
```

Open models also let users:

- Change models
- Experiment with model sizes
- Run entirely offline
- Customize behavior
- Choose a model appropriate for their hardware
- Avoid per-request AI costs

---

# 29. MVP Non-Goals

Do not build these in the first version:

- Automatic deletion
- Cloud synchronization
- User accounts
- Authentication
- Mobile application
- Gmail integration
- Slack integration
- Calendar integration
- OCR
- Image understanding
- Fine-tuning
- Multi-agent architecture
- Vector database
- Long-term memory

The MVP should remain:

> **One folder + one local model + one organization plan.**

---

# 30. Success Criteria

The MVP is successful if a user can:

1. Select a local folder.
2. Scan it.
3. See its files and metadata.
4. Detect duplicates.
5. Ask a local LM Studio model to organize it.
6. Receive folder recommendations.
7. Receive short tasks.
8. Receive priorities.
9. Review each recommendation.
10. Perform a dry run.
11. Apply approved changes.
12. Confirm that nothing was deleted.
13. Confirm that files never left the machine.

---

# 31. Example Demo

Start with:

```text
Downloads/

final_final.pdf
final_final_2.pdf
IMG_8291.png
IMG_8292.png
invoice_oct.pdf
invoice_old.pdf
meeting-notes.txt
project-proposal-v7.pdf
old-report.docx
todo.txt
random.pdf
contract_client.pdf
```

Sloth Organizer scans it.

The AI produces:

```text
📁 Projects
3 files

💰 Finance
2 files

📄 Documents
3 files

🖼️ Media
2 files

🔍 Review
2 files
```

Then:

```text
🔥 HIGH

Pay October invoice
Review client contract

🟡 MEDIUM

Finish project proposal
Review old report

🟢 LOW

Archive old screenshots
```

The user reviews the changes and clicks:

```text
🦥 Apply Approved Changes
```

The messy folder becomes organized.

---

# 32. The Pitch

## One sentence

> **Sloth Organizer is a local-first AI that cleans up your messy folders, figures out what actually needs your attention, and lets you deal with the rest later.**

## Hackathon angle

Most productivity tools try to help people do more.

**Sloth Organizer tries to help people care about fewer things.**

## Open-source angle

Because the AI runs locally through LM Studio, Sloth Organizer can inspect private files without requiring those files to be sent to a third-party AI service.

## Slow and Steady angle

> **The sloth doesn't rush through your files. It patiently figures out what matters, organizes the mess, and leaves you with a tiny list of things worth doing.**

---

# 33. Future Roadmap

## v0.2

- Image understanding
- More file formats
- Undo/rollback
- Organization history
- Custom organization rules

## v0.3

- Local semantic search
- "Ask my files"
- Watch folders
- Scheduled organization

## v0.4

- Gmail integration
- Calendar integration
- Slack/Discord exports

## v1.0

A persistent local AI file assistant that continuously keeps your digital workspace organized while minimizing the amount of work it asks from you.

---

# 34. Definition of Done

The MVP is complete when this works reliably:

```text
MESSY FOLDER
      ↓
SCAN
      ↓
LOCAL MODEL VIA LM STUDIO
      ↓
UNDERSTAND FILES
      ↓
ORGANIZATION PLAN
      ↓
SHORT TASKS
      ↓
PRIORITIES
      ↓
HUMAN APPROVAL
      ↓
DRY RUN
      ↓
APPLY
      ↓
CLEAN FOLDER
+
SMALL TODO LIST
```

**The user's workload after running Sloth Organizer should be smaller than it was before.**
