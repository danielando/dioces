# Deployment & Testing Guide

This guide walks through the full process of deploying the Policy Localisation Engine to Azure, from initial setup through to verifying the first production run.

---

## Prerequisites

- An Azure subscription with permissions to create resources
- Global Admin or Privileged Role Administrator access in Entra ID (for app registration and admin consent)
- SharePoint Online admin access (to create the site and lists)
- Azure CLI or Azure Portal access
- Node.js (for Azure Functions Core Tools) or VS Code with the Azure Functions extension
- Git and access to the [dioces repository](https://github.com/danielando/dioces)

---

## Phase 1: Entra ID App Registration

This creates an identity that the Function App uses to authenticate with SharePoint via Microsoft Graph.

### Step 1.1 — Register the application

1. Navigate to [Entra ID > App registrations](https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Click **New registration**
3. Configure:
   - **Name**: `Policy Localisation Engine`
   - **Supported account types**: Accounts in this organizational directory only (Single tenant)
   - **Redirect URI**: Leave blank
4. Click **Register**

### Step 1.2 — Record the identifiers

From the app's **Overview** page, copy and save:
- **Application (client) ID** → this becomes `AZURE_CLIENT_ID`
- **Directory (tenant) ID** → this becomes `AZURE_TENANT_ID`

### Step 1.3 — Create a client secret

1. Go to **Certificates & secrets** > **Client secrets** > **New client secret**
2. Description: `Policy Engine Secret`
3. Expiry: **24 months** (set a calendar reminder to rotate)
4. Click **Add**
5. Copy the **Value** immediately (it won't be shown again) → this becomes `AZURE_CLIENT_SECRET`

### Step 1.4 — Grant API permissions

1. Go to **API permissions** > **Add a permission**
2. Select **Microsoft Graph** > **Application permissions**
3. Search for and add: `Sites.ReadWrite.All`
4. Click **Add permissions**
5. Click **Grant admin consent for [your org]** (requires admin role)
6. Verify the status column shows a green tick for the permission

---

## Phase 2: SharePoint Site Setup

### Step 2.1 — Create the SharePoint site

1. Go to [SharePoint Admin Center](https://admin.microsoft.com/sharepoint)
2. Create a new **Team site** or **Communication site**
   - Name: `Policy Localisation` (or your preferred name)
   - Make note of the site URL (e.g., `https://contoso.sharepoint.com/sites/PolicyLocalisation`)

### Step 2.2 — Get the Site ID

Open a browser and navigate to:
```
https://graph.microsoft.com/v1.0/sites/{your-tenant}.sharepoint.com:/sites/{site-name}
```

Or use Graph Explorer at https://developer.microsoft.com/graph/graph-explorer:
```
GET https://graph.microsoft.com/v1.0/sites/contoso.sharepoint.com:/sites/PolicyLocalisation
```

Copy the `id` field from the response (format: `contoso.sharepoint.com,guid,guid`) → this becomes `SHAREPOINT_SITE_ID`

### Step 2.3 — Create the "School Directory" Microsoft List

1. In the SharePoint site, click **New** > **List** > **Blank list**
2. Name: `School Directory`
3. Add the following columns:

| Column Name | Column Type | Required | Notes |
|---|---|---|---|
| Title | Single line of text | Yes | Built-in column — used for the full school name |
| SchoolCode | Single line of text | Yes | Unique short code, e.g., `STM` |
| ShortName | Single line of text | Yes | Informal name, e.g., `St Mary's` |
| PrincipalName | Single line of text | Yes | e.g., `Mrs. Jane Smith` |
| PrincipalTitle | Single line of text | No | e.g., `Principal` or `Head of School` |
| SchoolAddress | Multiple lines of text (plain) | No | Full street address |
| Suburb | Single line of text | No | |
| State | Single line of text | No | |
| PostCode | Single line of text | No | |
| SchoolPhone | Single line of text | No | |
| SchoolEmail | Single line of text | No | |
| SchoolWebsite | Single line of text | No | |
| SchoolType | Choice | No | Values: `Primary`, `Secondary`, `P-12`, `Special` |
| Parish | Single line of text | No | |
| DiocesanRegion | Single line of text | No | |
| ABN | Single line of text | No | |
| EstablishedYear | Single line of text | No | |

4. Populate the list with data for all 43 schools

### Step 2.4 — Create the "Processing Log" Microsoft List

1. Click **New** > **List** > **Blank list**
2. Name: `Processing Log`
3. Add the following columns:

| Column Name | Column Type | Notes |
|---|---|---|
| Title | Single line of text | Auto-populated with `{SchoolCode}-{PolicyName}` |
| RunId | Single line of text | Unique identifier per run |
| RunDate | Date and time | When the run occurred |
| SchoolCode | Single line of text | |
| PolicyName | Single line of text | |
| Status | Choice | Values: `Success`, `Error`, `Skipped` |
| ErrorMessage | Multiple lines of text (plain) | |
| Duration | Number | Seconds to process |

### Step 2.5 — Create the Document Libraries

Create three document libraries:

1. **Policy Templates**
   - Click **New** > **Document library** > Name: `Policy Templates`
   - Upload all 19 `.docx` policy templates
   - Each template must use `{{ColumnName}}` placeholders (matching the School Directory column names)
   - Each template must contain a placeholder image named `logo_placeholder.png` in the header (top-right position)

2. **School Logos**
   - Click **New** > **Document library** > Name: `School Logos`
   - Upload 43 PNG logo files, each named `{SchoolCode}.png` (e.g., `STM.png`, `HFC.png`)

3. **Localised Policies**
   - Click **New** > **Document library** > Name: `Localised Policies`
   - Leave empty — the engine will create folders and upload documents here

---

## Phase 3: Prepare the Templates

### Step 3.1 — Add text placeholders

In each `.docx` template, use `{{ColumnName}}` placeholders anywhere you want school-specific data inserted. Available placeholders:

```
{{Title}}              — Full school name
{{SchoolCode}}         — Short code
{{ShortName}}          — Informal name
{{PrincipalName}}      — Principal's name
{{PrincipalTitle}}     — Principal's title
{{SchoolAddress}}      — Street address
{{Suburb}}             — Suburb
{{State}}              — State
{{PostCode}}           — Post code
{{SchoolPhone}}        — Phone number
{{SchoolEmail}}        — Email address
{{SchoolWebsite}}      — Website URL
{{SchoolType}}         — Primary / Secondary / P-12 / Special
{{Parish}}             — Parish name
{{DiocesanRegion}}     — Diocesan region
{{ABN}}                — ABN
{{EstablishedYear}}    — Year established
```

**Important**: Type each placeholder in one go — do not select part of a placeholder and change its formatting, as this can cause Word to split the placeholder across multiple XML elements.

### Step 3.2 — Add the logo placeholder image

1. Open each template in Word
2. Go to the **header** (double-click the header area)
3. Insert an image named `logo_placeholder.png` (any image will do — it gets replaced)
4. Position it **top-right** and size it to approximately **3.5 cm wide**
5. Save and upload to the Policy Templates library

---

## Phase 4: Provision the Azure Function App

### Step 4.1 — Create the Function App

1. Go to [Azure Portal](https://portal.azure.com) > **Create a resource** > **Function App**
2. Configure:
   - **Subscription**: Your subscription
   - **Resource Group**: Create new or use existing (e.g., `rg-policy-localisation`)
   - **Function App name**: `func-policy-localisation` (must be globally unique)
   - **Runtime stack**: Python
   - **Version**: 3.12
   - **Region**: Australia East (or closest to your users)
   - **Operating System**: Linux
   - **Hosting plan**: Consumption (Serverless)
3. Click **Review + create** > **Create**

### Step 4.2 — Configure application settings

1. Go to the Function App > **Configuration** > **Application settings**
2. Add the following settings:

| Name | Value |
|---|---|
| `AZURE_TENANT_ID` | From Phase 1, Step 1.2 |
| `AZURE_CLIENT_ID` | From Phase 1, Step 1.2 |
| `AZURE_CLIENT_SECRET` | From Phase 1, Step 1.3 |
| `SHAREPOINT_SITE_ID` | From Phase 2, Step 2.2 |

3. Click **Save**

### Step 4.3 — Deploy the code

#### Option A: Azure Functions Core Tools (CLI)

```bash
# Install Azure Functions Core Tools (if not already installed)
npm install -g azure-functions-core-tools@4

# Clone the repo
git clone https://github.com/danielando/dioces.git
cd dioces/function_app

# Deploy
func azure functionapp publish func-policy-localisation
```

#### Option B: VS Code

1. Install the **Azure Functions** extension for VS Code
2. Open the `function_app/` folder in VS Code
3. Click the Azure icon in the sidebar
4. Under **Functions**, click the deploy button (cloud with up arrow)
5. Select your Function App
6. Confirm the deployment

#### Option C: GitHub Actions (recommended for ongoing deployments)

1. In Azure Portal, go to Function App > **Deployment Center**
2. Source: **GitHub**
3. Organization: `danielando`
4. Repository: `dioces`
5. Branch: `main`
6. Azure generates a GitHub Actions workflow automatically
7. Future pushes to `main` will auto-deploy

### Step 4.4 — Get the Function Key

1. Go to Function App > **Functions** > **manual_trigger** (or `localise`)
2. Click **Get Function Url**
3. Copy the URL (includes the function key as a query parameter)
4. Save this — you'll use it to trigger runs

---

## Phase 5: Testing

### Test 1 — Local test with sample data (no Azure required)

This validates the core document engine works correctly.

```bash
# Clone and set up
git clone https://github.com/danielando/dioces.git
cd dioces
python -m venv .venv

# Activate venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Generate test fixtures (sample template + logos)
python scripts/create_test_template.py

# Run the local pipeline
python scripts/run_local.py \
  --templates tests/fixtures/templates \
  --logos tests/fixtures/logos \
  --output data/output \
  --schools-json tests/fixtures/sample_schools.json
```

**Expected output:**
```
Status   School   Policy                                Time
----------------------------------------------------------------------
OK       STM      Sample_Policy                        0.06s
OK       HFC      Sample_Policy                        0.03s
OK       SJV      Sample_Policy                        0.05s

Total: 3 | Success: 3 | Failed: 0
```

**Verify:** Open `data/output/STM - St Mary's Primary School/Sample_Policy.docx` in Word and confirm:
- [ ] All `{{Placeholder}}` text is replaced with school-specific data
- [ ] The header contains the STM logo (blue rectangle), not the grey placeholder
- [ ] Table data (School Code, Parish, ABN, Established) is populated
- [ ] Footer page numbers are intact

### Test 2 — Run the unit tests

```bash
cd dioces
python -m pytest -v
```

**Expected output:** 16 tests, all passing.

### Test 3 — Single school against live SharePoint

Before processing all 43 schools, test with one:

```bash
# Create .env file with your credentials
cp .env.example .env
# Edit .env with your actual values

# Run for a single school
python scripts/run_sharepoint.py --school STM
```

**Verify in SharePoint:**
- [ ] A folder `STM - St Mary's Primary School` exists in the **Localised Policies** library
- [ ] The folder contains all 19 localised policy documents
- [ ] Open one document and verify placeholders are replaced and logo is correct
- [ ] Check the **Processing Log** list — should have 19 entries with Status = `Success`

### Test 4 — Full run (all schools, all templates)

```bash
python scripts/run_sharepoint.py
```

**Expected:** 817 documents processed (19 × 43).

**Verify in SharePoint:**
- [ ] 43 folders exist in the **Localised Policies** library
- [ ] Each folder contains 19 documents
- [ ] Processing Log has 817 entries
- [ ] Spot-check 3-4 schools across different regions

### Test 5 — Idempotent re-run

Run the full pipeline again:

```bash
python scripts/run_sharepoint.py
```

**Verify:**
- [ ] No duplicate folders created
- [ ] Files are overwritten (check modified date in SharePoint)
- [ ] Processing Log has 817 **new** entries (append-only) with a different RunId

### Test 6 — Azure Function HTTP trigger

```bash
# Single school test
curl -X POST "https://func-policy-localisation.azurewebsites.net/api/localise?code=YOUR_FUNCTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{"schools": ["STM"]}'
```

**Expected response:**
```json
{"processed": 19, "success": 19, "failed": 0}
```

### Test 7 — Error handling

1. Temporarily remove one school's logo from the **School Logos** library
2. Run the pipeline for that school
3. **Verify:**
   - [ ] The pipeline reports validation errors and stops
   - [ ] No partial output is created for that school
4. Re-upload the logo

---

## Phase 6: Post-Deployment

### Share folders with schools

After the initial run, create sharing links for each school's folder:

```bash
python scripts/run_sharepoint.py --share-only
```

Or manually in SharePoint: right-click each school's folder > **Share** > set appropriate permissions.

### Set up monitoring

1. Go to Function App > **Application Insights**
2. Application Insights is enabled by default — click through to view:
   - **Live Metrics** — real-time execution monitoring
   - **Failures** — any errors during runs
   - **Performance** — execution times

### Schedule the annual run

The Azure Function includes a timer trigger set to run at **2:00 AM on January 15** each year (`0 0 2 15 1 *`). This is configured in `function_app.py` and will run automatically once deployed.

To change the schedule, modify the cron expression in `function_app.py` and redeploy.

### Rotate the client secret

The client secret expires after 24 months. Before expiry:

1. Go to Entra ID > App registrations > Policy Localisation Engine
2. Create a **new** client secret
3. Update the `AZURE_CLIENT_SECRET` app setting in the Function App
4. Verify with a test run
5. Delete the old secret

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Failed to acquire token` | Wrong tenant/client ID or expired secret | Check Entra ID app settings and rotate secret if needed |
| `List 'School Directory' not found` | List name mismatch or site ID wrong | Verify `SHAREPOINT_SITE_ID` and that the list name matches exactly |
| `Document library 'Policy Templates' not found` | Library name mismatch | Verify library names in SharePoint match the code constants exactly |
| `Logo not found for {SchoolCode}` | Missing or misnamed logo PNG | Ensure the file is named `{SchoolCode}.png` (case-sensitive) |
| Unreplaced `{{Placeholder}}` in output | Placeholder split across Word runs | Re-type the placeholder in the template in a single action without formatting changes |
| Footer page numbers missing | Simple field code was destroyed | Use Insert > Quick Parts > Field > Page in Word to create complex field codes |
| HTTP 429 from Graph API | Throttled during large batch | Automatic — the client retries using the Retry-After header |
| Timer trigger not firing | Function App is stopped or in wrong time zone | Check Function App is running; verify the WEBSITE_TIME_ZONE app setting |
