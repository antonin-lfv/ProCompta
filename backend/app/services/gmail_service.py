import base64
import logging
from datetime import date, datetime
from email.utils import parsedate_to_datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings

logger = logging.getLogger(__name__)


def _build_service():
    creds = Credentials(
        token=None,
        refresh_token=settings.gmail_refresh_token,
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )
    try:
        creds.refresh(Request())
    except Exception as exc:
        raise RuntimeError(f"Impossible de rafraîchir le token OAuth Gmail : {exc}") from exc
    return build("gmail", "v1", credentials=creds)


def check_connection() -> tuple[bool, str]:
    """Returns (True, email) on success, (False, error_message) on failure."""
    if not settings.gmail_configured:
        return False, "Variables GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET / GMAIL_REFRESH_TOKEN manquantes dans .env"
    try:
        service = _build_service()
        profile = service.users().getProfile(userId="me").execute()
        return True, profile["emailAddress"]
    except Exception as exc:
        return False, str(exc)


def _iter_parts(payload: dict):
    if "parts" in payload:
        for part in payload["parts"]:
            yield from _iter_parts(part)
    else:
        yield payload


def fetch_invoices(
    sender: str,
    subject_contains: str | None,
    attachment_name_contains: str | None,
    already_imported: set[str],
    after_date: date | None = None,
    before_date: date | None = None,
) -> list[dict]:
    """
    Returns list of {
        "message_id": str,
        "filename": str,
        "data": bytes,
        "date": datetime,
        "subject": str,
    }
    for each unprocessed PDF attachment found.
    """
    service = _build_service()

    q_parts = [f"from:{sender}", "has:attachment"]
    if subject_contains:
        q_parts.append(f'subject:"{subject_contains}"')
    if after_date:
        q_parts.append(f"after:{after_date.strftime('%Y/%m/%d')}")
    if before_date:
        q_parts.append(f"before:{before_date.strftime('%Y/%m/%d')}")
    q = " ".join(q_parts)

    messages: list[dict] = []
    page_token = None
    while True:
        kwargs: dict = {"userId": "me", "q": q, "maxResults": 500}
        if page_token:
            kwargs["pageToken"] = page_token
        response = service.users().messages().list(**kwargs).execute()
        messages.extend(response.get("messages", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    results = []
    for msg_ref in messages:
        msg_id = msg_ref["id"]
        if msg_id in already_imported:
            continue

        try:
            msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        except Exception:
            logger.exception("Failed to fetch Gmail message %s", msg_id)
            continue

        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        subject = headers.get("Subject", "")
        date_str = headers.get("Date", "")
        try:
            email_date = parsedate_to_datetime(date_str)
        except Exception:
            email_date = datetime.now()

        for part in _iter_parts(msg["payload"]):
            filename = part.get("filename", "")
            if not filename.lower().endswith(".pdf"):
                continue
            if attachment_name_contains:
                if attachment_name_contains.lower() not in filename.lower():
                    continue

            att_id = part["body"].get("attachmentId")
            if att_id:
                try:
                    att = service.users().messages().attachments().get(
                        userId="me", messageId=msg_id, id=att_id
                    ).execute()
                    data = base64.urlsafe_b64decode(att["data"])
                except Exception:
                    logger.exception("Failed to fetch attachment %s from message %s", att_id, msg_id)
                    continue
            else:
                data_b64 = part["body"].get("data", "")
                if not data_b64:
                    continue
                data = base64.urlsafe_b64decode(data_b64)

            results.append({
                "message_id": msg_id,
                "filename": filename,
                "data": data,
                "date": email_date,
                "subject": subject,
            })

    return results
