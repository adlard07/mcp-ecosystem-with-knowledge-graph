"""MCP tools for reading and updating Gmail messages."""

from __future__ import annotations

from typing import Any

from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.connectors import google_credentials, mcp

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _service():
    return build("gmail", "v1", credentials=google_credentials(GMAIL_SCOPES))


def _execute(request):
    try:
        return request.execute()
    except RefreshError as error:
        raise RuntimeError(f"Gmail OAuth refresh failed: {error}") from error
    except HttpError as error:
        raise RuntimeError(
            f"Gmail API error ({error.resp.status}): {error.reason or 'request failed'}"
        ) from error


def _clean_labels(labels: list[str] | None) -> list[str]:
    cleaned = [label.strip() for label in (labels or []) if label and label.strip()]
    return list(dict.fromkeys(cleaned))


@mcp.tool()
def gmail_search(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search Gmail messages and return their headers and snippets."""
    query = (query or "").strip()
    if not query:
        raise ValueError("query must not be empty.")
    if not 1 <= max_results <= 500:
        raise ValueError("max_results must be between 1 and 500.")

    service = _service()
    response = _execute(
        service.users().messages().list(userId="me", q=query, maxResults=max_results)
    )

    messages: list[dict[str, Any]] = []
    for item in response.get("messages", []):
        message = _execute(
            service.users().messages().get(
                userId="me",
                id=item["id"],
                format="metadata",
                metadataHeaders=["Subject", "From", "To", "Date"],
            )
        )
        headers = {
            header["name"].lower(): header.get("value", "")
            for header in message.get("payload", {}).get("headers", [])
        }
        messages.append(
            {
                "id": message["id"],
                "thread_id": message.get("threadId"),
                "subject": headers.get("subject", ""),
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "date": headers.get("date", ""),
                "snippet": message.get("snippet", ""),
                "label_ids": message.get("labelIds", []),
            }
        )
    return messages


@mcp.tool()
def gmail_update_labels(
    message_id: str,
    add_labels: list[str] | None = None,
    remove_labels: list[str] | None = None,
) -> dict[str, Any]:
    """Add or remove labels on a Gmail message.

    System label IDs such as UNREAD, INBOX, STARRED, and IMPORTANT can be used
    directly; custom labels require their label IDs.
    """
    message_id = (message_id or "").strip()
    if not message_id:
        raise ValueError("message_id must not be empty.")
    add_labels = _clean_labels(add_labels)
    remove_labels = _clean_labels(remove_labels)
    if not add_labels and not remove_labels:
        raise ValueError("Provide at least one label to add or remove.")

    service = _service()
    message = _execute(
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": add_labels, "removeLabelIds": remove_labels},
        )
    )
    return {"id": message["id"], "label_ids": message.get("labelIds", [])}
