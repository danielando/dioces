# Policy Localisation Engine — Technical Overview

## Problem

817 customised policy documents (19 templates × 43 schools) need to be generated annually from Word templates stored in SharePoint. Each document requires school-specific text replacement and logo insertion into the document header.

## Tech Stack

- **Python 3.12** — runtime
- **docxtpl** (python-docx-template) — Word document templating (Jinja2-based placeholder replacement + image swap in headers)
- **Microsoft Graph API** — all SharePoint read/write operations (lists, document libraries, file upload, folder sharing)
- **MSAL** — Entra ID app-only authentication (client credentials flow)
- **Azure Functions** (Python v2) — hosting (HTTP trigger for on-demand, timer trigger for annual schedule)

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Azure Function (Python)             │
│         HTTP trigger  |  Timer trigger           │
└──────────────────────┬──────────────────────────┘
                       │
              ┌────────▼────────┐
              │   Orchestrator  │
              └────────┬────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  Graph API       Document        Graph API
  (download)       Engine          (upload)
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
     Replace     Replace    Validate
   {{text}}    header logo   & log
```

### Data Flow

1. Azure Function triggers (on-demand or scheduled)
2. Orchestrator reads school data from the **School Directory** Microsoft List via Graph API
3. Downloads 19 policy templates and 43 school logos from SharePoint document libraries
4. For each school × template combination (817 total):
   - Replaces all `{{Placeholder}}` text in body, headers, footers, and tables
   - Swaps the placeholder logo image in the header with the school's logo
5. Uploads rendered documents to the **Localised Policies** library (one folder per school)
6. Writes a processing log entry for every document (success/failure, duration, errors)

## SharePoint Site Components

| Component | Type | Purpose |
|---|---|---|
| School Directory | Microsoft List | School metadata (name, address, principal, phone, email, etc.) |
| Policy Templates | Document Library | 19 master .docx templates containing `{{Placeholder}}` tokens |
| School Logos | Document Library | 43 PNG files named by school code (e.g. `STM.png`) |
| Localised Policies | Document Library | Output — one folder per school containing 19 localised docs |
| Processing Log | Microsoft List | Audit trail — status, errors, and duration per document per run |

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Layered architecture** | Document engine is pure Python with no network dependency — fully unit-testable locally without SharePoint access |
| **docxtpl over raw python-docx** | Handles Jinja2 templating, Word's run-splitting problem, and `replace_pic()` for image swapping natively |
| **Idempotent re-runs** | Folder creation checks for existing; file upload overwrites; processing log is append-only with unique run IDs |
| **Graph API via raw `requests`** | Simpler than the Microsoft Graph SDK for straightforward CRUD; full control over retry and throttling logic |
| **Folders over Document Sets** | Easier to create/manage via Graph API; shareable; identical UX in modern SharePoint |
| **Placeholder convention `{{ColumnName}}`** | Maps directly to Microsoft List column names — no separate mapping table needed |

## Authentication

- **App-only (daemon)** via MSAL client credentials flow
- Requires an **Entra ID app registration** with `Sites.ReadWrite.All` application permission + admin consent
- No user sign-in required — runs unattended

## Project Structure

```
src/policy_localiser/
├── engine/              # Layer 1: Pure document engine (no network)
│   ├── models.py        #   SchoolRecord, ProcessingResult dataclasses
│   ├── renderer.py      #   docxtpl rendering + logo replacement
│   └── validator.py     #   Pre-flight validation
├── graph/               # Layer 2: Microsoft Graph API
│   ├── auth.py          #   MSAL token acquisition
│   ├── client.py        #   HTTP client with retry/throttle
│   ├── sharepoint_lists.py
│   └── sharepoint_files.py
├── orchestrator/        # Layer 3: Pipeline orchestration
│   ├── pipeline.py      #   Local pipeline (for testing)
│   └── sharepoint_pipeline.py  # Full SharePoint pipeline
└── sharing/             # Layer 4: Post-processing
    └── folder_sharing.py  # Create sharing links per school folder

function_app/            # Azure Function entry point
scripts/                 # CLI runners for local and SharePoint modes
tests/                   # 16 unit tests covering all Layer 1 logic
```

## Running Modes

| Mode | Command | Purpose |
|---|---|---|
| **Local test** | `python scripts/run_local.py --templates ... --logos ... --output ... --schools-json ...` | Test document rendering with local files, no SharePoint needed |
| **SharePoint CLI** | `python scripts/run_sharepoint.py` | Run full pipeline against live SharePoint from the command line |
| **Azure Function (HTTP)** | `POST /api/localise` with optional `{"schools": [...], "templates": [...]}` | On-demand trigger with optional filters |
| **Azure Function (Timer)** | Cron: `0 0 2 15 1 *` | Scheduled annual run (Jan 15 at 2:00 AM) |

## Prerequisites for Deployment

1. SharePoint site with all 5 components created (2 lists + 3 document libraries)
2. Entra ID app registration with `Sites.ReadWrite.All` + admin consent
3. Templates authored with `{{ColumnName}}` placeholders and `logo_placeholder.png` in the header
4. School logos uploaded as `{SchoolCode}.png`
5. Azure Function App provisioned (Python 3.12 runtime)
