"""Google Drive incremental sync for runbook markdown files."""

from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.config import (
    GOOGLE_DRIVE_ENABLED,
    GOOGLE_DRIVE_FOLDER_ID,
    GOOGLE_SERVICE_ACCOUNT_FILE,
    RUNBOOKS_DIR,
)
from app.models import RunbookSource, SessionLocal, utcnow

logger = logging.getLogger("runbook-ingestion.drive")

MARKDOWN_MIME = {
    "text/markdown",
    "text/plain",
    "application/vnd.google-apps.document",
}


def _drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _parse_drive_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def sync_google_drive_folder() -> dict:
    """Download changed *.md runbooks from a shared Drive folder."""
    if not GOOGLE_DRIVE_ENABLED:
        return {"enabled": False, "synced": 0, "skipped": 0, "message": "drive_disabled"}

    if not GOOGLE_DRIVE_FOLDER_ID:
        raise RuntimeError("GOOGLE_DRIVE_FOLDER_ID is required when GOOGLE_DRIVE_ENABLED=true")

    if not Path(GOOGLE_SERVICE_ACCOUNT_FILE).is_file():
        raise RuntimeError(f"Google service account file missing: {GOOGLE_SERVICE_ACCOUNT_FILE}")

    RUNBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    service = _drive_service()

    page_token = None
    synced = 0
    skipped = 0

    while True:
        response = (
            service.files()
            .list(
                q=f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, md5Checksum)",
                pageToken=page_token,
            )
            .execute()
        )

        for item in response.get("files", []):
            name = item.get("name", "")
            if not name.endswith(".md"):
                continue
            mime = item.get("mimeType", "")
            if mime not in MARKDOWN_MIME and not name.endswith(".md"):
                skipped += 1
                continue

            file_id = item["id"]
            source_key = f"drive:{file_id}"
            remote_modified = _parse_drive_time(item.get("modifiedTime"))
            remote_hash = item.get("md5Checksum")

            with SessionLocal() as session:
                existing = session.get(RunbookSource, source_key)
                if (
                    existing
                    and existing.content_hash == remote_hash
                    and existing.remote_modified_at == remote_modified
                ):
                    skipped += 1
                    continue

            content = _download_file(service, item)
            dest = RUNBOOKS_DIR / name
            dest.write_bytes(content)
            content_hash = remote_hash or _sha256(content)

            with SessionLocal() as session:
                row = session.get(RunbookSource, source_key) or RunbookSource(
                    source_key=source_key,
                    source_type="google_drive",
                    file_name=name,
                )
                row.remote_modified_at = remote_modified
                row.content_hash = content_hash
                row.local_path = str(dest)
                row.last_synced_at = utcnow()
                session.merge(row)
                session.commit()

            synced += 1
            logger.info("Synced Drive runbook %s (%s)", name, file_id)

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return {"enabled": True, "synced": synced, "skipped": skipped}


def _download_file(service, item: dict) -> bytes:
    mime = item.get("mimeType", "")
    file_id = item["id"]
    if mime == "application/vnd.google-apps.document":
        data = service.files().export(fileId=file_id, mimeType="text/plain").execute()
        return data if isinstance(data, bytes) else str(data).encode("utf-8")

    request = service.files().get_media(fileId=file_id)
    from googleapiclient.http import MediaIoBaseDownload

    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


def _sha256(content: bytes) -> str:
    import hashlib

    return hashlib.sha256(content).hexdigest()
