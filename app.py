"""A small command-line client for the private CloudVault Supabase bucket."""

from pathlib import Path
import mimetypes
import os


BUCKET_NAME = "cloud-files"
PAGE_SIZE = 100


def permission_hint():
    """Explain the least-privilege Storage permissions used by this app."""
    print(
        "Check the Storage policies on storage.objects for bucket_id "
        f"'{BUCKET_NAME}': INSERT for uploads, SELECT for listing and downloads, "
        "and SELECT plus DELETE for deletions. Restrict policies to the intended "
        "role and users. This app does not change policies or make the bucket public."
    )
    print(
        "A service_role/secret key bypasses Storage RLS. Keep it only in a local "
        "trusted environment; never commit it or put it in a browser app."
    )


def report_error(action, error):
    """Print an operation error and add guidance for likely RLS failures."""
    message = str(error).strip() or error.__class__.__name__
    print(f"Error: {action} failed: {message}")

    lowered = message.lower()
    permission_markers = (
        "permission",
        "row-level security",
        "row level security",
        "unauthorized",
        "not authorized",
        "forbidden",
        "status code 401",
        "status code 403",
        "new row violates",
    )
    if any(marker in lowered for marker in permission_markers):
        permission_hint()
    elif any(marker in lowered for marker in ("invalid api key", "invalid key", "invalid jwt")):
        print("Check that SUPABASE_URL and SUPABASE_KEY belong to the same Supabase project.")


def local_file_path(raw_path):
    """Expand a user-entered path, allowing paths wrapped in quotes."""
    cleaned = raw_path.strip().strip('"').strip("'")
    if not cleaned:
        raise ValueError("Please enter a file path.")
    return Path(cleaned).expanduser()


def list_all_files(bucket, folder=""):
    """Return file paths in the bucket, including files in subfolders."""
    files = []
    offset = 0

    while True:
        entries = bucket.list(
            folder,
            {
                "limit": PAGE_SIZE,
                "offset": offset,
                "sortBy": {"column": "name", "order": "asc"},
            },
        )
        if not entries:
            break

        for entry in entries:
            name = entry.get("name")
            if not isinstance(name, str) or not name:
                continue

            object_path = f"{folder}/{name}" if folder else name
            if entry.get("metadata") is not None:
                files.append(object_path)
            else:
                # Supabase represents folders as entries without file metadata.
                files.extend(list_all_files(bucket, object_path))

        if len(entries) < PAGE_SIZE:
            break
        offset += len(entries)

    return files


def choose_cloud_file(bucket):
    """Display available files and return the selected storage path."""
    files = sorted(list_all_files(bucket))
    if not files:
        print("No files are stored in the bucket yet.")
        return None

    print("\nFiles in cloud-files:")
    for index, name in enumerate(files, start=1):
        print(f"  {index}. {name}")

    choice = input("Choose a file number (or press Enter to cancel): ").strip()
    if not choice:
        print("Cancelled.")
        return None

    try:
        selected_index = int(choice)
    except ValueError:
        print("Please enter one of the displayed file numbers.")
        return None

    if selected_index < 1 or selected_index > len(files):
        print("That file number is not in the list.")
        return None

    return files[selected_index - 1]


def upload_file(bucket):
    """Upload a local file to the bucket root without replacing existing files."""
    try:
        source = local_file_path(input("Path of the file to upload: "))
        if not source.exists():
            print("Error: that file path does not exist.")
            return
        if not source.is_file():
            print("Error: the path must point to a file, not a folder.")
            return

        content_type, _ = mimetypes.guess_type(source.name)
        with source.open("rb") as file_data:
            bucket.upload(
                path=source.name,
                file=file_data,
                file_options={
                    "content-type": content_type or "application/octet-stream",
                    "upsert": "false",
                },
            )

        print(f"Success: {source.name} uploaded to {BUCKET_NAME}.")
    except (OSError, ValueError) as error:
        print(f"Error: could not read the selected file: {error}")
    except Exception as error:  # Supabase client and network errors
        report_error("Upload", error)


def list_files(bucket):
    """List stored files in the private bucket."""
    try:
        files = sorted(list_all_files(bucket))
        if not files:
            print("No files are stored in the bucket yet.")
            return

        print(f"\nFiles in {BUCKET_NAME}:")
        for name in files:
            print(f"  - {name}")
    except Exception as error:  # Supabase client and network errors
        report_error("Listing files", error)


def download_file(bucket):
    """Download a selected cloud file to a local path."""
    try:
        remote_path = choose_cloud_file(bucket)
        if remote_path is None:
            return

        default_name = Path(remote_path).name
        raw_destination = input(
            f"Save to path (Enter for ./{default_name}): "
        )
        destination = (
            local_file_path(raw_destination)
            if raw_destination.strip()
            else Path(default_name)
        )

        if destination.exists() and destination.is_dir():
            print("Error: the download destination is a folder.")
            return
        if not destination.parent.exists():
            print("Error: the destination folder does not exist.")
            return
        if destination.exists():
            confirm = input(f"{destination} already exists. Overwrite it? (y/N): ")
            if confirm.strip().lower() != "y":
                print("Cancelled; the existing local file was left unchanged.")
                return

        data = bucket.download(remote_path)
        destination.write_bytes(data)
        print(f"Success: downloaded {remote_path} to {destination}.")
    except (OSError, ValueError) as error:
        print(f"Error: could not save the downloaded file: {error}")
    except Exception as error:  # Supabase client and network errors
        report_error("Download", error)


def delete_file(bucket):
    """Delete a selected cloud file after asking for confirmation."""
    try:
        remote_path = choose_cloud_file(bucket)
        if remote_path is None:
            return

        confirm = input(f"Delete {remote_path} from the cloud? (y/N): ")
        if confirm.strip().lower() != "y":
            print("Cancelled; the cloud file was left unchanged.")
            return

        bucket.remove([remote_path])
        print(f"Success: {remote_path} deleted from {BUCKET_NAME}.")
    except Exception as error:  # Supabase client and network errors
        report_error("Delete", error)


def main():
    """Load local configuration and run the interactive menu."""
    try:
        from dotenv import load_dotenv
        from supabase import create_client
    except ImportError as error:
        print(f"Missing dependency: {error.name}")
        print("Install project dependencies with: python -m pip install -r requirements.txt")
        return

    load_dotenv(Path(__file__).resolve().parent / ".env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_KEY are required.")
        print("Add them to a local .env file or set them in your environment.")
        return

    try:
        supabase = create_client(url, key)
        bucket = supabase.storage.from_(BUCKET_NAME)
    except Exception as error:
        report_error("Supabase client setup", error)
        return

    print("CloudVault - Cloud File Storage System")
    print(f"Ready to use the private '{BUCKET_NAME}' bucket.")
    print("Network access and permissions are checked when you choose an operation.")

    while True:
        print(
            "\nMenu"
            "\n1. Upload a file"
            "\n2. List cloud files"
            "\n3. Download a file"
            "\n4. Delete a file"
            "\n5. Exit"
        )
        try:
            choice = input("Choose an option (1-5): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if choice == "1":
            upload_file(bucket)
        elif choice == "2":
            list_files(bucket)
        elif choice == "3":
            download_file(bucket)
        elif choice == "4":
            delete_file(bucket)
        elif choice == "5":
            print("Goodbye.")
            break
        else:
            print("Please choose a number from 1 to 5.")


if __name__ == "__main__":
    main()
