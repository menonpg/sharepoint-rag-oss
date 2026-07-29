# Setup Guide — from zero to a working SharePoint RAG index

This walks you click-by-click through getting the tool working end to end,
including the Microsoft authentication that trips most people up.

There are two parts:

1. **[Part A — Get a tenant you administer](#part-a--get-a-tenant-you-administer)**
   (skip if you already have admin on the target Microsoft 365 tenant)
2. **[Part B — Register the app and grant permissions](#part-b--register-the-app)**
3. **[Part C — Configure and run the tool](#part-c--configure-and-run-the-tool)**
4. **[Troubleshooting](#troubleshooting)**

> **Why you can't use a personal account.** App-only (headless) access to
> SharePoint requires the Microsoft Graph *application* permission
> `Sites.Read.All`, which only exists in a **work/school (Entra ID) tenant** and
> must be **admin-consented**. Personal Microsoft accounts (outlook.com,
> hotmail.com) have no Entra tenant and cannot do this.

---

## Part A — Get a tenant you administer

If you do **not** have admin rights on the tenant that owns the SharePoint site,
create a free sandbox tenant to build and test against.

1. Go to the **Microsoft 365 Developer Program**:
   <https://developer.microsoft.com/microsoft-365/dev-program>
2. Click **Join now** and sign in with any Microsoft account.
3. Choose **Set up E5 subscription** → **Instant sandbox**. This creates a brand
   new tenant like `yourname.onmicrosoft.com` where **you are the global admin**,
   pre-loaded with sample users and SharePoint sites.
4. Note the admin username (e.g. `admin@yourname.onmicrosoft.com`) and password.
5. Open **SharePoint**: go to `https://yourname.sharepoint.com`, open (or create)
   a site, open its **Documents** library, and upload a few test files
   (PDF / DOCX / TXT). This is what you'll index.

You now have: a site URL, admin rights, and test content. Continue to Part B.

> For the **real** target tenant (e.g. a corporate `fraunhofercse` tenant), a
> tenant admin must perform Part B. You can send them this section. Consider the
> `Sites.Selected` variant (see the note at the end of Part B) so the app is
> scoped to a single site instead of the whole tenant — far easier to approve.

---

## Part B — Register the app

Do this in the tenant that owns the SharePoint site (your sandbox, or the real
tenant if you're admin there).

### B1. Create the app registration

1. Go to the **Microsoft Entra admin center**: <https://entra.microsoft.com>
2. Left nav → **Identity** → **Applications** → **App registrations**.
3. Click **+ New registration**.
   - **Name**: `sharepoint-rag-indexer`
   - **Supported account types**: *Accounts in this organizational directory only*
     (single tenant).
   - **Redirect URI**: leave blank (app-only needs none).
4. Click **Register**.
5. On the app **Overview** page, copy these two values — you'll need them later:
   - **Directory (tenant) ID** → this becomes `SP_TENANT_ID`
   - **Application (client) ID** → this becomes `SP_CLIENT_ID`

### B2. Create a client secret

1. In the app, go to **Certificates & secrets** → **Client secrets** tab.
2. Click **+ New client secret**, add a description, choose an expiry, **Add**.
3. **Immediately copy the `Value`** (not the Secret ID) → this becomes
   `SP_CLIENT_SECRET`. It is shown only once; if you lose it, delete and make a
   new one.

### B3. Add the Graph permission

1. Go to **API permissions** → **+ Add a permission**.
2. Choose **Microsoft Graph** → **Application permissions** (not *Delegated*).
3. Search for and check **`Sites.Read.All`**. (Optionally also `Files.Read.All`.)
4. Click **Add permissions**.

### B4. Grant admin consent

1. Still on **API permissions**, click **Grant admin consent for <tenant>**.
2. Confirm. The **Status** column for `Sites.Read.All` must turn into a green
   check reading *Granted for <tenant>*.

> **Until this shows green, every Graph call returns HTTP 403.** This step
> requires a tenant admin. This is the single most common reason the tool
> "doesn't work".

### (Optional, recommended for production) Scope to one site with `Sites.Selected`

`Sites.Read.All` grants read to *every* site in the tenant. For a commercial /
least-privilege deployment, use `Sites.Selected` instead:

1. In **B3**, add the application permission **`Sites.Selected`** (and grant
   admin consent as in B4).
2. A tenant admin then grants the app read on just the target site by calling
   Graph once (e.g. via Graph Explorer):

   ```http
   POST https://graph.microsoft.com/v1.0/sites/{site-id}/permissions
   Content-Type: application/json

   {
     "roles": ["read"],
     "grantedToIdentities": [
       { "application": { "id": "<SP_CLIENT_ID>", "displayName": "sharepoint-rag-indexer" } }
     ]
   }
   ```

   Get `{site-id}` from `GET /sites/{host}:/sites/{name}`. After this, the app
   can read only that site — nothing else in the tenant.

---

## Part C — Configure and run the tool

### C1. Install (one time)

```bash
cd sharepoint-rag-oss
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
```

### C2. Fill in `.env`

Copy the template if you haven't already, then edit `.env`:

```bash
cp .env.example .env   # if .env doesn't exist yet
```

Set the three SharePoint values from Part B (put them in `.env` yourself — never
share secrets):

```dotenv
SP_TENANT_ID=<Directory (tenant) ID from B1>
SP_CLIENT_ID=<Application (client) ID from B1>
SP_CLIENT_SECRET=<client secret Value from B2>
```

The Azure OpenAI values for embeddings and chat are already present in the
template — replace them with your own keys and **rotate any key that was ever
shared in plaintext**.

### C3. Find your site URL and folder path

- **Site URL**: the part up to the site name, e.g.
  `https://yourname.sharepoint.com/sites/Research`
- **Folder**: the path **relative to the document library root** — do *not*
  include the `Documents` / `Shared Documents` segment.

  | Files live in (SharePoint UI) | Use `--folder` |
  |---|---|
  | Documents (whole library) | omit it / `""` |
  | Documents › Knowledge Base | `"Knowledge Base"` |
  | Documents › Policies › 2026 | `"Policies/2026"` |

  Tip: if you copied a long SharePoint URL, the folder is the part of the `id=`
  parameter after `.../Shared Documents/`.

### C4. Validate auth (fast, indexes nothing)

```bash
sp-rag doctor --site-url "https://yourname.sharepoint.com/sites/Research" \
              --folder "Knowledge Base"
```

Expected on success:

```
Token acquired:  yes
Site id:         yourname.sharepoint.com,<guid>,<guid>
Drive id:        b!....
Folder item id:  01....
Visible files (first N):
  - example.pdf
  - notes.docx

All checks passed. You're ready to run 'sp-rag sync'.
```

If it fails, jump to [Troubleshooting](#troubleshooting).

### C5. Index and query

```bash
# Cache the target for future syncs
sp-rag init --site-url "https://yourname.sharepoint.com/sites/Research" \
            --folder "Knowledge Base"

# Download changed files, extract, embed, index (run on a schedule / cron)
sp-rag sync

# Ask questions
sp-rag query "What does the onboarding policy say about equipment?"

# Inspect state at any time
sp-rag status
```

### C6. Keep it fresh

`sync` is incremental — it only reprocesses changed files (via Graph delta +
content hashing). Schedule it, e.g. every 15 minutes:

```cron
*/15 * * * * cd /path/to/sharepoint-rag-oss && ./.venv/bin/sp-rag sync >> sync.log 2>&1
```

---

## Troubleshooting

Run `sp-rag doctor` first — it pinpoints which stage fails.

| Symptom | Meaning | Fix |
|---|---|---|
| `authentication failed: ... invalid_client` | Wrong client ID or secret | Re-copy `SP_CLIENT_ID`; create a fresh secret (B2) and update `SP_CLIENT_SECRET` |
| `authentication failed: ... Unable to get authority ...` | `SP_TENANT_ID` wrong/placeholder | Use the Directory (tenant) ID GUID from B1 |
| `site/folder resolution failed: HTTP 403` | Permission not consented | Do **B4** (Grant admin consent); confirm green check on `Sites.Read.All` |
| `site/folder resolution failed: HTTP 404` | Wrong site URL or folder path | Verify the site URL; remember the folder is **relative to the library root** (no `Documents/`) |
| `doctor` shows files but `query` says "No documents" | You haven't indexed yet | Run `sp-rag sync` |
| Only some file types indexed | Unsupported extension | Supported: PDF, DOCX, PPTX, HTML, MD, TXT, CSV, JSON |
| Secret stopped working after a while | Client secret expired | Create a new secret (B2), update `.env` |

Still stuck? Run the diagnostic with full output (no `tail`) and read the first
error line — it names the exact stage and HTTP code.
