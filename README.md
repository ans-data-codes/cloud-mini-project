# CloudVault — Cloud File Storage System

CloudVault is a small local Python command-line application for managing files in the existing private Supabase Storage bucket named `cloud-files`.

## Requirements

- Python 3.9 or newer
- A Supabase project with the private `cloud-files` bucket already created
- A Supabase URL and API key with the Storage permissions needed for the actions you want to use

## Install and configure

Open this project folder in the VS Code terminal, then create and activate a virtual environment in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the two required packages:

```powershell
python -m pip install -r requirements.txt
```

Create a local `.env` file in the project folder with your project details:

```text
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-api-key
```

The `.env` file is ignored by Git. Keep its key private and never commit it. Environment variables already set in the terminal take precedence over values in `.env`.

The application does not create or change buckets or policies. Keep `cloud-files` private. Use credentials appropriate for a trusted local script. A service role or secret key bypasses Storage row-level security, so store one only in this local environment and never use it in a browser or commit it to source control. A publishable/anon key needs Storage policies that explicitly allow the operations you use; the app will not create permissive anonymous policies for you.

## Run

From the project folder with the virtual environment active, run:

```powershell
python app.py
```

Choose from the menu to upload, list, download, delete, or exit. Uploads go to the bucket root and do not overwrite an existing cloud file. Downloads use the file name in the current folder by default; you can enter another local path. The app asks before overwriting a local file or deleting a cloud file.

## Storage permissions

For a private bucket, configure least-privilege policies on Supabase's `storage.objects` table for the role and users represented by your key:

- Upload a new file: `INSERT`
- List or download files: `SELECT`
- Delete a file: `SELECT` and `DELETE`

Scope policies to `bucket_id = 'cloud-files'` and to the intended user or role. Upserting is disabled, so uploads do not require overwrite permissions. If an operation reports a permission error, check the key type, role, and matching bucket-scoped policies in the Supabase Dashboard. Do not make the bucket public to fix a permissions error.

## Test the operations manually

After configuring credentials and permissions, start the app and use a disposable, non-sensitive test file:

1. Choose **1**, enter the local file path, and confirm the upload success message.
2. Choose **2** and confirm the file appears in the bucket listing.
3. Choose **3**, select the file, and save it to a temporary local path. Compare the downloaded file with the original.
4. Choose **4**, select that test file, and confirm deletion. List the bucket again to verify it is gone.

Cloud operations require valid credentials, network access, and suitable Storage policies. They have not been run as part of preparing this project.

## Cloud computing concept

The Python application and its text interface run locally on your computer. Supabase Storage is hosted remotely in the cloud. Files travel between the local application and the cloud over the internet through the Supabase API. This demonstrates **Storage as a Service (STaaS)**: a cloud provider stores and manages files that an application can access on demand.
