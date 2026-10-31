"""
MIT License

Copyright (c) 2026 Tushar Teredesai

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import argparse
import sys

# Check dependencies before running the script.
MISSING_PACKAGES = []

try:
    import yaml
except ImportError:
    MISSING_PACKAGES.append("PyYAML (https://pypi.org)")

try:
    from imap_tools import AND, MailBox
except ImportError:
    MISSING_PACKAGES.append("imap-tools (https://pypi.org)")

if MISSING_PACKAGES:
    print("Error: Missing required dependencies!")
    print("Please install the following package(s) to run this script:\n")
    for package in MISSING_PACKAGES:
        print(f"  * {package}")
    sys.exit(1)

# Mapping of special folder types to IMAP attributes and common folder name fallbacks
SPECIAL_FOLDER_MAPPINGS = {
    "inbox": {"attributes": ["\\Inbox"], "names": ["inbox"]},
    "spam": {"attributes": ["\\Junk", "\\Spam"], "names": ["junk", "spam", "bulk", "bulk mail"]},
    "trash": {"attributes": ["\\Trash"], "names": ["trash", "bin", "deleted messages", "deleted"]},
    "sent": {"attributes": ["\\Sent"], "names": ["sent", "sent items", "sent messages"]},
    "drafts": {"attributes": ["\\Drafts"], "names": ["drafts"]},
    "archive": {"attributes": ["\\Archive"], "names": ["archive", "archives"]}
}

def resolve_folder_name(mailbox, folder_spec, default="special:inbox"):
    """
    Resolves a folder specification. 
    If folder_spec starts with 'special:', attempts to auto-detect the folder 
    on the server using IMAP flags or common names. Otherwise, returns folder_spec as-is.
    If folder_spec is empty/None, uses the default (which evaluates special:inbox).
    """
    if not folder_spec:
        folder_spec = default

    # Check if it's designated as a special folder lookup
    spec_lower = folder_spec.strip().lower()
    if spec_lower.startswith("special:"):
        target_type = spec_lower.split(":", 1)[1].strip()
        if target_type not in SPECIAL_FOLDER_MAPPINGS:
            print(f"Warning: Unknown special folder type '{target_type}'. Falling back to 'inbox'.")
            target_type = "inbox"

        criteria = SPECIAL_FOLDER_MAPPINGS[target_type]
        
        try:
            # List all folders and their attributes from the mailbox
            folders = list(mailbox.folder.list())
            
            # 1. Try matching by IMAP attributes first (most reliable)
            for f in folders:
                if any(attr.lower() in [a.lower() for a in criteria["attributes"]] for attr in f.attributes):
                    print(f"Auto-detected special folder [{target_type}] via attribute -> '{f.name}'")
                    return f.name

            # 2. Fallback to common naming conventions if attributes aren't set
            for f in folders:
                if f.name.lower() in criteria["names"]:
                    print(f"Auto-detected special folder [{target_type}] via name match -> '{f.name}'")
                    return f.name
                    
            print(f"Warning: Could not auto-detect special folder for '{target_type}'. Falling back to 'INBOX'.")
        except Exception as e:
            print(f"Error while querying server folders for special type '{target_type}': {e}")
            
        return "INBOX"

    # Standard non-special folder works as-is
    return folder_spec

def generate_sample_yaml(output_path):
    """Write an annotated sample configuration for both move modes."""
    sample_content = """# Configuration file for the IMAP Email Processing Tool
# Supported filter criteria include standard imap-tools keys such as:
#   seen: true/false
#   flagged: true/false
#   date_gte: "2023-01-01" (Greater than or equal to date)
#   date_lt: "2024-01-01"  (Less than date)
#   subject: "keyword"
#   from_: "sender@example.com"
# Refer to https://github.com/ikvk/imap_tools for full filter reference.
#
# Special Folders: You can use explicit folder names (e.g., "Bulk", "Archive") 
# or auto-detect standard folders using the prefix "special:" followed by:
#   - special:inbox (Default if left blank)
#   - special:spam (or junk)
#   - special:trash (or bin)
#   - special:sent
#   - special:drafts
#   - special:archive

email_jobs:
  # =========================================================================
  # CONFIGURATION TYPE 1: Internal Move (Same Server)
  # =========================================================================
  - name: "Auto-detect Spam to Archive Example"
    imap_server: "imap.example.com"       # Required; IMAP server hostname
    port_number: 993                      # Optional; defaults to 993
    email_address: "user@example.com"     # Required; email username
    password: "your-app-password"         # Password; or app password
    source_folder: "special:spam"         # Auto-detects Spam/Junk folder
    target_folder: "special:archive"      # Auto-detects Archive folder
    max_messages: 50                      # Optional; null means no limit

    # Optional filters to selectively match emails.
    filters:
      seen: false

  # =========================================================================
  # CONFIGURATION TYPE 2: Cross-Server Migration
  # =========================================================================
  - name: "Cross-Server Migration Example"
    # Source server details (source_folder defaults to special:inbox if omitted)
    imap_server: "imap.source.com"
    port_number: 993
    email_address: "user@source.com"
    password: "source-app-password"
    source_folder: "special:spam"         
    max_messages: 250                     # Defaults to 100 for cross-server jobs

    # Destination details (dest_target_folder defaults to special:inbox if omitted)
    dest_imap_server: "imap.dest.com"
    dest_port_number: 993
    dest_email_address: "user@dest.com"
    dest_password: "dest-app-password"
    dest_target_folder: "ImportedBulk"    

    filters:
      seen: true
      date_gte: "2023-01-01"
"""
    try:
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(sample_content)
        print(f"Successfully created a template configuration file at: '{output_path}'")
    except OSError as error:
        print(f"Error generating sample file: {error}")
        sys.exit(1)

    sys.exit(0)

def load_config(config_path):
    """Load and return the YAML configuration file."""
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Error: The configuration file '{config_path}' was not found.")
        sys.exit(1)
    except yaml.YAMLError as error:
        print(f"Error parsing YAML file: {error}")
        sys.exit(1)

    if config is None:
        return {}

    if not isinstance(config, dict):
        print("Error: The configuration file must contain a YAML mapping.")
        sys.exit(1)

    return config

def validate_and_normalize_job(job, idx):
    """
    Validate a single job's configuration structure and rules.
    Returns a tuple: (is_valid: bool, error_message: str or None)
    """
    if not isinstance(job, dict):
        return False, f"Job #{idx}: Error - Job entry must be a YAML mapping."

    job_name = job.get("name", f"Job #{idx}")
    server = job.get("imap_server")
    email = job.get("email_address")
    password = job.get("password")
    
    # Default source/target folders to special:inbox if omitted or blank
    source = job.get("source_folder") or "special:inbox"

    if not all([server, email, password]):
        return False, f"Job '{job_name}': Error - Missing base connection details (imap_server, email_address, or password)."

    max_messages = job.get("max_messages")
    if max_messages is not None:
        try:
            if int(max_messages) < 1:
                raise ValueError
        except ValueError:
            return False, f"Job '{job_name}': Error - 'max_messages' must be a positive integer."

    is_cross_server = bool(job.get("dest_imap_server"))
    if is_cross_server:
        dest_server = job.get("dest_imap_server")
        dest_email = job.get("dest_email_address")
        dest_password = job.get("dest_password")
        dest_target = job.get("dest_target_folder") or "special:inbox"

        if not all([dest_server, dest_email, dest_password]):
            return False, f"Job '{job_name}': Error - Cross-server job missing destination credentials (dest_imap_server, dest_email_address, or dest_password)."

        if (
            server.lower() == dest_server.lower()
            and email.lower() == dest_email.lower()
            and source.lower() == dest_target.lower()
        ):
            return False, f"Job '{job_name}': Error - Source folder and destination folder cannot be identical on the same account."
    else:
        target = job.get("target_folder") or "special:inbox"
        if source.lower() == target.lower():
            return False, f"Job '{job_name}': Error - Source folder and target folder are both resolving to/set as '{source}' on the same internal account."

    return True, None

def validate_configuration(config_path):
    """Perform comprehensive validation on all jobs in the configuration file."""
    print(f"Validating configuration file: '{config_path}'...")
    config = load_config(config_path)
    jobs = config.get("email_jobs", [])

    if not jobs:
        print("Validation Error: No 'email_jobs' found in the configuration.")
        return False

    is_valid = True
    for idx, job in enumerate(jobs, start=1):
        valid, err_msg = validate_and_normalize_job(job, idx)
        if not valid:
            print(err_msg)
            is_valid = False

    if is_valid:
        print("Configuration validation successful! No errors found.")
        return True

    print("Configuration validation failed with errors.")
    return False

def process_internal_job(
    mailbox, source, target, search_criteria, max_messages, job_name, dry_run=False
):
    """Move messages between folders on the same server, preserving original dates."""
    limit_text = f"up to {max_messages}" if max_messages else "all matching"
    print(f"Searching for {limit_text} matches in internal folder '{source}'...")

    # Fetch full message objects (bulk=False) to access bytes, flags, and dates
    matched_emails = list(mailbox.fetch(search_criteria, limit=max_messages, bulk=False))

    if not matched_emails:
        print("No matching emails found.")
        return

    print(f"Found {len(matched_emails)} email(s). Moving to '{target}'...")
    if dry_run:
        print(f"[DRY RUN] Would move {len(matched_emails)} email(s) from '{source}' to '{target}'.")
        return

    successful_count = 0
    for message in matched_emails:
        try:
            # Append email explicitly preserving flags and original date/timestamp
            mailbox.append(
                message.bytes,
                folder=target,
                flag_set=message.flags,
                dt=message.date,
            )

            # Delete immediately from source folder
            mailbox.delete(message.uid)
            successful_count += 1
        except Exception as move_error:
            subject = (message.subject or "")[:30]
            print(
                f"Failed to move email UID {message.uid} (Subject: {subject}). "
                f"Skipping removal. Error: {move_error}"
            )

    if successful_count > 0:
        print(f"Successfully processed internal job: {job_name} ({successful_count} emails moved)")
    else:
        print("No emails were successfully moved.")

def process_cross_server_job(
    src_mailbox, source, job, search_criteria, max_messages, job_name, dry_run=False
):
    """Copy messages one-by-one to another server, then remove successfully copied emails immediately."""
    dest_server = job.get("dest_imap_server")
    dest_port = job.get("dest_port_number", 993)
    dest_email = job.get("dest_email_address")
    dest_password = job.get("dest_password")
    
    raw_dest_target = job.get("dest_target_folder") or "special:inbox"

    limit_text = f"up to {max_messages}" if max_messages else "all matching"
    print(f"Searching for {limit_text} matches in source folder '{source}'...")

    matched_emails = list(
        src_mailbox.fetch(search_criteria, limit=max_messages, bulk=False)
    )

    if not matched_emails:
        print("No matching emails found.")
        return

    print(f"Found {len(matched_emails)} email(s). Connecting to destination server {dest_server}...")

    if dry_run:
        print(f"[DRY RUN] Would process {len(matched_emails)} email(s) for cross-server migration to {dest_server}.")
        return

    try:
        with MailBox(dest_server, port=dest_port).login(
            dest_email, dest_password
        ) as dest_mailbox:
            # Resolve destination target folder (defaults to special:inbox if omitted)
            dest_target = resolve_folder_name(dest_mailbox, raw_dest_target, default="special:inbox")

            if not dest_mailbox.folder.exists(dest_target):
                print(f"Creating missing target folder '{dest_target}' on destination server...")
                dest_mailbox.folder.create(dest_target)

            successful_count = 0
            print("Streaming and uploading emails iteratively (copy -> delete)...")

            for message in matched_emails:
                try:
                    # Append email preserving flags and original date/timestamp explicitly
                    dest_mailbox.append(
                        message.bytes,
                        folder=dest_target,
                        flag_set=message.flags,
                        dt=message.date,
                    )

                    # Delete immediately from source to minimize duplicates if interrupted
                    src_mailbox.delete(message.uid)
                    successful_count += 1
                except Exception as upload_error:
                    subject = (message.subject or "")[:30]
                    print(
                        f"Failed to process email UID {message.uid} (Subject: {subject}). "
                        f"Skipping removal. Error: {upload_error}"
                    )

            if successful_count > 0:
                print(f"Successfully migrated and cleaned up {successful_count} email(s) for job: {job_name}")
            else:
                print("No emails were successfully transferred and removed.")

    except Exception as destination_error:
        print(f"Destination server critical error: {destination_error}")

def process_email_jobs(config_path, dry_run=False):
    """Run each validated email-processing job in the configuration."""
    config = load_config(config_path)
    jobs = config.get("email_jobs", [])

    if not jobs:
        print("No jobs found in the configuration file.")
        return

    if dry_run:
        print("\n*** RUNNING IN DRY RUN MODE - NO CHANGES WILL BE MADE ***\n")

    for idx, job in enumerate(jobs, start=1):
        valid, err_msg = validate_and_normalize_job(job, idx)
        if not valid:
            print(f"Skipping job: {err_msg}")
            continue

        job_name = job.get("name", f"Job #{idx}")
        print("\n" + "=" * 50)
        print(f"Starting Job: {job_name}")
        print("=" * 50)

        server = job.get("imap_server")
        port = job.get("port_number", 993)
        email = job.get("email_address")
        password = job.get("password")
        
        raw_source = job.get("source_folder") or "special:inbox"
        raw_target = job.get("target_folder") or "special:inbox"

        is_cross_server = bool(job.get("dest_imap_server"))
        max_messages = job.get("max_messages")

        if max_messages is not None:
            max_messages = int(max_messages)

        if is_cross_server and max_messages is None:
            max_messages = 100

        try:
            print(f"Connecting to source {server} on port {port} ({email})...")
            
            with MailBox(server, port=port).login(email, password) as src_mailbox:
                # Dynamically resolve source and target folders (defaults to special:inbox)
                source = resolve_folder_name(src_mailbox, raw_source, default="special:inbox")
                
                if not is_cross_server:
                    target = resolve_folder_name(src_mailbox, raw_target, default="special:inbox")
                    if source.lower() == target.lower():
                        print(f"Error: Source folder and resolved target folder are both '{source}'. Skipping job.")
                        continue

                # Set current folder to the resolved source
                src_mailbox.folder.set(source)

                filters = job.get("filters")
                if filters:
                    print("Connected. Parsing search filters...")
                    search_criteria = AND(**filters)
                else:
                    print("Connected. No filters provided, matching ALL emails...")
                    search_criteria = "ALL"

                if is_cross_server:
                    process_cross_server_job(
                        src_mailbox,
                        source,
                        job,
                        search_criteria,
                        max_messages,
                        job_name,
                        dry_run=dry_run,
                    )
                else:
                    process_internal_job(
                        src_mailbox,
                        source,
                        target,
                        search_criteria,
                        max_messages,
                        job_name,
                        dry_run=dry_run,
                    )
        except Exception as error:
            print(f"An error occurred while processing the job: {error}")

def main():
    """Parse command-line arguments and run the requested operation."""
    parser = argparse.ArgumentParser(
        description=(
            "moveMyEmails: Move emails between two folders - internal or cross-server"
        ),
        epilog=(
            "License: MIT | Developer: Tushar Teredesai\n\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--sample",
        metavar="FILE_PATH",
        help="Generate a sample YAML file containing both move templates and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the job execution without modifying any mailboxes.",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate the configuration syntax and logic without running jobs.",
    )
    parser.add_argument(
        "config_file",
        nargs="?",
        help="Path to the YAML configuration file containing your operations.",
    )

    args = parser.parse_args()

    if args.sample:
        generate_sample_yaml(args.sample)

    if not args.config_file:
        parser.print_help()
        sys.exit(1)

    if args.validate_config:
        is_valid = validate_configuration(args.config_file)
        sys.exit(0 if is_valid else 1)

    process_email_jobs(args.config_file, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
